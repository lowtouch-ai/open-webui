from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from open_webui.utils.auth import get_verified_user, get_admin_user
from open_webui.utils.vault import (
    store_agent_connection_in_vault,
    get_agent_connection_from_vault,
    delete_agent_connection_from_vault,
    list_agent_keys_from_vault,
    get_vault_client,
    sanitize_agent_id,
    format_secret_path,
    ENABLE_VAULT_INTEGRATION
)
from open_webui.config import ENABLE_VAULT_INTEGRATION as VAULT_CONFIG
from open_webui.models.users import Users
from loguru import logger

router = APIRouter()


class AgentConnectionCreate(BaseModel):
    key_name: str
    key_value: str
    agent_id: Optional[str] = None
    is_common: bool = False


class AgentConnectionResponse(BaseModel):
    key_id: str
    key_name: str
    agent_id: Optional[str] = None
    is_common: bool = False
    created_at: datetime
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None


class AgentConnectionUpdate(BaseModel):
    key_name: Optional[str] = None
    key_value: Optional[str] = None
    agent_id: Optional[str] = None
    is_common: Optional[bool] = None


def _make_key_id(user_id: str, key_name: str, agent_id: Optional[str], is_common: bool) -> str:
    """Build a stable key_id from components.

    Format: {user_id}:{scope}:{key_name}
    where scope is 'COMMON', 'default', or the sanitized agent_id.
    Using ':' as delimiter avoids ambiguity with '_' inside sanitized agent names.
    """
    if is_common:
        scope = "COMMON"
    elif agent_id:
        scope = sanitize_agent_id(agent_id)
    else:
        scope = "default"
    return f"{user_id}:{scope}:{key_name}"


def _parse_key_id(key_id: str):
    """Parse a key_id back into (user_id, scope, key_name)."""
    parts = key_id.split(':', 2)
    if len(parts) != 3:
        raise HTTPException(status_code=400, detail="Invalid key_id format")
    user_id, scope, key_name = parts
    is_common = scope == "COMMON"
    agent_id = None if scope in ("COMMON", "default") else scope
    return user_id, scope, key_name, agent_id, is_common


@router.post("/", response_model=AgentConnectionResponse)
async def create_agent_connection(
    connection: AgentConnectionCreate,
    user=Depends(get_verified_user)
):
    """Create or update a key in Vault."""
    try:
        if not connection.key_name or not connection.key_value:
            raise HTTPException(status_code=400, detail="Key name and value are required")

        if not connection.key_name.replace('_', '').isalnum():
            raise HTTPException(status_code=400, detail="Key name must be alphanumeric with underscores only")

        if connection.is_common and user.role != "admin":
            raise HTTPException(status_code=403, detail="Only administrators can create common connections")

        vault_connection = {
            "name": connection.key_name,
            "value": connection.key_value,
            "agent_id": connection.agent_id,
            "is_common": connection.is_common
        }

        if VAULT_CONFIG.value:
            success = store_agent_connection_in_vault(vault_connection, user.id)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to store key in Vault")

        logger.info(f"Stored key {connection.key_name} for user {user.id} (agent: {connection.agent_id or ('common' if connection.is_common else 'default')})")

        key_id = _make_key_id(user.id, connection.key_name, connection.agent_id, connection.is_common)

        return AgentConnectionResponse(
            key_id=key_id,
            key_name=connection.key_name,
            agent_id=connection.agent_id,
            is_common=connection.is_common,
            created_at=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating agent connection: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/debug", response_model=dict)
async def debug_agent_connections(user=Depends(get_admin_user)):
    """Debug endpoint to check Vault configuration and connection details."""
    try:
        debug_info = {
            "vault_config_enabled": VAULT_CONFIG.value,
            "vault_client_available": False,
            "vault_connection_test": False,
            "vault_secrets_test": False,
            "error_details": None,
            "user_processing": [],
            "all_users_from_db": [],
            "final_connections": []
        }

        if VAULT_CONFIG.value:
            vault_client = get_vault_client()
            if vault_client:
                debug_info["vault_client_available"] = True

                try:
                    connection_result = vault_client.connect()
                    debug_info["vault_connection_test"] = connection_result

                    if connection_result:
                        try:
                            response = vault_client.client.secrets.kv.v1.list_secrets(
                                path="users",
                                mount_point=vault_client.mount_path
                            )
                            debug_info["vault_secrets_test"] = True
                            debug_info["users_path_response"] = response

                            # Get all users from database
                            try:
                                all_users_result = Users.get_users()
                                if hasattr(all_users_result, 'users'):
                                    users_list = all_users_result.users
                                elif isinstance(all_users_result, dict) and 'users' in all_users_result:
                                    users_list = all_users_result['users']
                                elif isinstance(all_users_result, list):
                                    users_list = all_users_result
                                else:
                                    users_list = []

                                all_users = {u.id: u for u in users_list}
                                debug_info["all_users_from_db"] = [{"id": u.id, "name": u.name, "email": u.email} for u in users_list]
                            except Exception as e:
                                debug_info["users_fetch_error"] = str(e)
                                all_users = {}

                            # Process each user found in Vault
                            if response and 'data' in response and 'keys' in response['data']:
                                for user_id in response['data']['keys']:
                                    if user_id.endswith('/'):
                                        user_id = user_id[:-1]

                                    user_info = all_users.get(user_id)
                                    user_debug = {
                                        "vault_user_id": user_id,
                                        "user_found_in_db": user_info is not None,
                                        "user_name": user_info.name if user_info else None,
                                        "user_email": user_info.email if user_info else None,
                                        "connections": []
                                    }

                                    try:
                                        # List agent-level secrets for this user
                                        user_response = vault_client.client.secrets.kv.v1.list_secrets(
                                            path=f"users/{user_id}",
                                            mount_point=vault_client.mount_path
                                        )

                                        user_debug["user_secrets_response"] = user_response

                                        if user_response and 'data' in user_response and 'keys' in user_response['data']:
                                            for agent_scope in user_response['data']['keys']:
                                                agent_scope_clean = agent_scope.rstrip('/')
                                                is_common = agent_scope_clean == "COMMON"
                                                agent_id = None if agent_scope_clean in ("COMMON", "default") else agent_scope_clean

                                                # Read the agent secret to enumerate keys
                                                try:
                                                    agent_secret = vault_client.get_secret(f"users/{user_id}/{agent_scope_clean}")
                                                    if agent_secret:
                                                        for key_name in agent_secret.keys():
                                                            connection_info = {
                                                                "agent_scope": agent_scope_clean,
                                                                "key_name": key_name,
                                                                "is_common": is_common,
                                                                "agent_id": agent_id
                                                            }
                                                            user_debug["connections"].append(connection_info)
                                                            debug_info["final_connections"].append({
                                                                "key_id": _make_key_id(user_id, key_name, agent_id, is_common),
                                                                "key_name": key_name,
                                                                "agent_id": agent_id,
                                                                "is_common": is_common,
                                                                "user_id": user_id,
                                                                "user_name": user_info.name if user_info else None,
                                                                "user_email": user_info.email if user_info else None
                                                            })
                                                except Exception as e:
                                                    user_debug["connections"].append({"agent_scope": agent_scope_clean, "error": str(e)})

                                    except Exception as e:
                                        user_debug["user_secrets_error"] = str(e)

                                    debug_info["user_processing"].append(user_debug)

                        except Exception as e:
                            debug_info["vault_secrets_test"] = False
                            debug_info["secrets_error"] = str(e)

                except Exception as e:
                    debug_info["connection_error"] = str(e)
            else:
                debug_info["error_details"] = "Vault client is None"
        else:
            debug_info["error_details"] = "Vault integration is disabled in config"

        return debug_info

    except Exception as e:
        logger.error(f"Error in debug endpoint: {str(e)}")
        return {"error": str(e)}


@router.get("/status", response_model=dict)
async def get_agent_connections_status(user=Depends(get_verified_user)):
    """Get the status of agent connections integration."""
    return {
        "vault_enabled": VAULT_CONFIG.value,
        "vault_available": False if not VAULT_CONFIG.value else (get_vault_client() is not None and get_vault_client().connect()),
        "message": "Vault integration is required for agent connections" if not VAULT_CONFIG.value else "Vault integration is available"
    }


@router.get("/", response_model=List[AgentConnectionResponse])
async def list_agent_connections(user=Depends(get_verified_user)):
    """List keys for a user."""
    try:
        connections = []

        if VAULT_CONFIG.value:
            vault_client = get_vault_client()
            if vault_client and vault_client.connect():
                try:
                    # List agent-level entries under users/{user_id}/
                    user_path = f"users/{user.id}"
                    response = vault_client.client.secrets.kv.v1.list_secrets(
                        path=user_path,
                        mount_point=vault_client.mount_path
                    )
                    if response and 'data' in response and 'keys' in response['data']:
                        for agent_scope in response['data']['keys']:
                            agent_scope_clean = agent_scope.rstrip('/')
                            is_common = agent_scope_clean == "COMMON"
                            agent_id = None if agent_scope_clean in ("COMMON", "default") else agent_scope_clean

                            # Read the agent secret to enumerate individual keys
                            try:
                                agent_secret = vault_client.get_secret(f"{user_path}/{agent_scope_clean}")
                                if agent_secret:
                                    for key_name in agent_secret.keys():
                                        key_id = _make_key_id(user.id, key_name, agent_id, is_common)
                                        connections.append(AgentConnectionResponse(
                                            key_id=key_id,
                                            key_name=key_name,
                                            agent_id=agent_id,
                                            is_common=is_common,
                                            created_at=datetime.now()
                                        ))
                            except Exception as e:
                                logger.debug(f"Failed to read agent secret {agent_scope_clean} for user {user.id}: {str(e)}")

                except Exception as e:
                    logger.debug(f"No agent connections found for user {user.id}: {str(e)}")

        logger.info(f"Listed {len(connections)} agent connections for user {user.id}")

        return connections

    except Exception as e:
        logger.error(f"Error listing agent connections: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/admin/all", response_model=List[AgentConnectionResponse])
async def list_all_agent_connections(user=Depends(get_admin_user)):
    """List all agent connections from all users (admin only)."""
    try:
        connections = []

        if VAULT_CONFIG.value:
            vault_client = get_vault_client()
            if vault_client and vault_client.connect():
                try:
                    response = vault_client.client.secrets.kv.v1.list_secrets(
                        path="users",
                        mount_point=vault_client.mount_path
                    )

                    if response and 'data' in response and 'keys' in response['data']:
                        # Get all user information once
                        all_users_result = Users.get_users()
                        if hasattr(all_users_result, 'users'):
                            users_list = all_users_result.users
                        elif isinstance(all_users_result, dict) and 'users' in all_users_result:
                            users_list = all_users_result['users']
                        else:
                            users_list = []
                        all_users = {u.id: u for u in users_list}

                        for user_id in response['data']['keys']:
                            if user_id.endswith('/'):
                                user_id = user_id[:-1]

                            user_info = all_users.get(user_id)

                            try:
                                user_response = vault_client.client.secrets.kv.v1.list_secrets(
                                    path=f"users/{user_id}",
                                    mount_point=vault_client.mount_path
                                )

                                if user_response and 'data' in user_response and 'keys' in user_response['data']:
                                    for agent_scope in user_response['data']['keys']:
                                        agent_scope_clean = agent_scope.rstrip('/')
                                        is_common = agent_scope_clean == "COMMON"
                                        agent_id = None if agent_scope_clean in ("COMMON", "default") else agent_scope_clean

                                        try:
                                            agent_secret = vault_client.get_secret(f"users/{user_id}/{agent_scope_clean}")
                                            if agent_secret:
                                                for key_name in agent_secret.keys():
                                                    key_id = _make_key_id(user_id, key_name, agent_id, is_common)
                                                    connections.append(AgentConnectionResponse(
                                                        key_id=key_id,
                                                        key_name=key_name,
                                                        agent_id=agent_id,
                                                        is_common=is_common,
                                                        created_at=datetime.now(),
                                                        user_id=user_id,
                                                        user_name=user_info.name if user_info else None,
                                                        user_email=user_info.email if user_info else None
                                                    ))
                                        except Exception as e:
                                            logger.debug(f"Failed to read agent secret {agent_scope_clean} for user {user_id}: {str(e)}")

                            except Exception as e:
                                logger.debug(f"No agent connections found for user {user_id}: {str(e)}")

                except Exception as e:
                    logger.debug(f"No agent connections found: {str(e)}")
        else:
            logger.info("Vault integration disabled, checking config-based agent connections")

        logger.info(f"Admin listed {len(connections)} agent connections from all users")

        return connections

    except Exception as e:
        logger.error(f"Error listing all agent connections: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{key_id}", response_model=dict)
async def get_agent_connection(
    key_id: str,
    user=Depends(get_verified_user)
):
    """Get a specific agent connection by key_id."""
    try:
        user_id, scope, key_name, agent_id, is_common = _parse_key_id(key_id)

        if user_id != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")

        if VAULT_CONFIG.value:
            value = get_agent_connection_from_vault(
                name=key_name,
                user_id=user_id,
                is_common=is_common,
                agent_id=agent_id
            )

            if value is None:
                raise HTTPException(status_code=404, detail="Key not found")

            return {
                "key_id": key_id,
                "key_name": key_name,
                "key_value": value,
                "agent_id": agent_id,
                "is_common": is_common
            }
        else:
            raise HTTPException(status_code=503, detail="Vault integration not enabled")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent connection: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{key_id}", response_model=AgentConnectionResponse)
async def update_agent_connection(
    key_id: str,
    connection: AgentConnectionUpdate,
    user=Depends(get_verified_user)
):
    """Update an existing agent connection."""
    try:
        user_id, scope, current_key_name, agent_id, is_common = _parse_key_id(key_id)

        if user_id != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")

        # Get current value if not updating it
        current_value = None
        if not connection.key_value and VAULT_CONFIG.value:
            current_value = get_agent_connection_from_vault(
                name=current_key_name,
                user_id=user_id,
                is_common=is_common,
                agent_id=agent_id
            )
            if current_value is None:
                raise HTTPException(status_code=404, detail="Key not found")

        new_key_name = connection.key_name or current_key_name
        new_key_value = connection.key_value or current_value
        new_agent_id = connection.agent_id if connection.agent_id is not None else agent_id
        new_is_common = connection.is_common if connection.is_common is not None else is_common

        if new_key_name != current_key_name and not new_key_name.replace('_', '').isalnum():
            raise HTTPException(status_code=400, detail="Key name must be alphanumeric with underscores only")

        if new_is_common and not is_common and user.role != "admin":
            raise HTTPException(status_code=403, detail="Only administrators can create common connections")

        # If key name or scope changed, delete old key first
        scope_changed = (
            new_agent_id != agent_id or
            new_is_common != is_common
        )
        if new_key_name != current_key_name or scope_changed:
            if VAULT_CONFIG.value:
                delete_agent_connection_from_vault(
                    name=current_key_name,
                    user_id=user_id,
                    is_common=is_common,
                    agent_id=agent_id
                )

        vault_connection = {
            "name": new_key_name,
            "value": new_key_value,
            "agent_id": new_agent_id,
            "is_common": new_is_common
        }

        if VAULT_CONFIG.value:
            success = store_agent_connection_in_vault(vault_connection, user_id)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to update key in Vault")

        new_key_id = _make_key_id(user_id, new_key_name, new_agent_id, new_is_common)

        logger.info(f"Updated key {current_key_name} -> {new_key_name} for user {user_id}")

        return AgentConnectionResponse(
            key_id=new_key_id,
            key_name=new_key_name,
            agent_id=new_agent_id,
            is_common=new_is_common,
            created_at=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating agent connection: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{key_id}", response_model=dict)
async def delete_agent_connection(
    key_id: str,
    user=Depends(get_verified_user)
):
    """Delete a key from Vault."""
    try:
        user_id, scope, key_name, agent_id, is_common = _parse_key_id(key_id)

        if user_id != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")

        if VAULT_CONFIG.value:
            success = delete_agent_connection_from_vault(
                name=key_name,
                user_id=user_id,
                is_common=is_common,
                agent_id=agent_id
            )

            if not success:
                raise HTTPException(status_code=500, detail="Failed to delete key from Vault")

        logger.info(f"Deleted key {key_name} for user {user_id} (agent: {agent_id or ('common' if is_common else 'default')})")

        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting agent connection: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
