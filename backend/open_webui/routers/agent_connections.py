from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from open_webui.utils.auth import get_verified_user, get_admin_user
from open_webui.utils.vault import (
    store_agent_connection_in_vault,
    get_agent_connection_from_vault,
    delete_agent_connection_from_vault,
    get_vault_client,
    sanitize_agent_id,
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


@router.post("/", response_model=AgentConnectionResponse)
async def create_agent_connection(
    connection: AgentConnectionCreate,
    user=Depends(get_verified_user)
):
    """Create or update a key in Vault."""
    try:
        # Validate input
        if not connection.key_name or not connection.key_value:
            raise HTTPException(status_code=400, detail="Key name and value are required")
        
        # Validate key name (alphanumeric and underscores only)
        if not connection.key_name.replace('_', '').isalnum():
            raise HTTPException(status_code=400, detail="Key name must be alphanumeric with underscores only")
        
        # Check if user is admin when creating common connections
        if connection.is_common and user.role != "admin":
            raise HTTPException(status_code=403, detail="Only administrators can create common connections")
        
        # Prepare connection data for vault
        vault_connection = {
            "name": connection.key_name,
            "value": connection.key_value,
            "agent_id": connection.agent_id,
            "is_common": connection.is_common
        }
        
        # Store in vault if enabled
        if VAULT_CONFIG.value:
            success = store_agent_connection_in_vault(vault_connection, user.id)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to store key in Vault")
        
        # Log the operation
        logger.info(f"Stored key {connection.key_name} for user {user.id} (agent: {connection.agent_id or 'common' if connection.is_common else 'default'})")
        
        # key_id format: "{user_id}|{key_name}|{agent_scope}" — '|' can't appear in any component
        agent_scope = "COMMON" if connection.is_common else (
            sanitize_agent_id(connection.agent_id) if connection.agent_id else "default"
        )
        key_id = f"{user.id}|{connection.key_name}|{agent_scope}"
        
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
                    # Test connection
                    connection_result = vault_client.connect()
                    debug_info["vault_connection_test"] = connection_result
                    
                    if connection_result:
                        # Test listing secrets
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
                                debug_info["users_result_type"] = str(type(all_users_result))
                                debug_info["users_result_keys"] = list(all_users_result.keys()) if isinstance(all_users_result, dict) else str(all_users_result)
                                
                                # Handle different return types
                                if hasattr(all_users_result, 'users'):
                                    # UserListResponse object
                                    users_list = all_users_result.users
                                elif isinstance(all_users_result, dict) and 'users' in all_users_result:
                                    # Dictionary with users key
                                    users_list = all_users_result['users']
                                elif isinstance(all_users_result, list):
                                    # Direct list of users
                                    users_list = all_users_result
                                else:
                                    debug_info["users_parsing_error"] = f"Unexpected users result type: {type(all_users_result)}"
                                    users_list = []
                                
                                all_users = {u.id: u for u in users_list}
                                debug_info["all_users_from_db"] = [{"id": u.id, "name": u.name, "email": u.email} for u in users_list]
                                
                            except Exception as e:
                                debug_info["users_fetch_error"] = str(e)
                                all_users = {}
                                debug_info["all_users_from_db"] = []
                            
                            # Process each user found in Vault (two-level listing)
                            if response and 'data' in response and 'keys' in response['data']:
                                for user_id in response['data']['keys']:
                                    user_id = user_id.rstrip('/')

                                    user_info = all_users.get(user_id)
                                    user_debug = {
                                        "vault_user_id": user_id,
                                        "user_found_in_db": user_info is not None,
                                        "user_name": user_info.name if user_info else None,
                                        "user_email": user_info.email if user_info else None,
                                        "connections": []
                                    }

                                    try:
                                        # Level 1: list agent folders under users/{user_id}/
                                        agent_response = vault_client.client.secrets.kv.v1.list_secrets(
                                            path=f"users/{user_id}",
                                            mount_point=vault_client.mount_path
                                        )
                                        if agent_response and 'data' in agent_response and 'keys' in agent_response['data']:
                                            for agent_folder in agent_response['data']['keys']:
                                                agent_scope = agent_folder.rstrip('/')
                                                is_common = (agent_scope == "COMMON")
                                                agent_id = None if agent_scope in ("COMMON", "default") else agent_scope

                                                # Level 2: list key names under that agent folder
                                                try:
                                                    key_response = vault_client.client.secrets.kv.v1.list_secrets(
                                                        path=f"users/{user_id}/{agent_scope}",
                                                        mount_point=vault_client.mount_path
                                                    )
                                                    if key_response and 'data' in key_response and 'keys' in key_response['data']:
                                                        for key_name in key_response['data']['keys']:
                                                            connection_info = {
                                                                "agent_scope": agent_scope,
                                                                "key_name": key_name,
                                                                "is_common": is_common,
                                                                "agent_id": agent_id
                                                            }
                                                            user_debug["connections"].append(connection_info)
                                                            debug_info["final_connections"].append({
                                                                "key_id": f"{user_id}|{key_name}|{agent_scope}",
                                                                "key_name": key_name,
                                                                "agent_id": agent_id,
                                                                "is_common": is_common,
                                                                "user_id": user_id,
                                                                "user_name": user_info.name if user_info else None,
                                                                "user_email": user_info.email if user_info else None
                                                            })
                                                except Exception as e:
                                                    user_debug.setdefault("key_list_errors", []).append(
                                                        f"{agent_scope}: {e}"
                                                    )
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


def _parse_connections_for_user(vault_client, user_id: str, user_info=None) -> list:
    """Two-level Vault listing: users/{user_id}/ → agent folders → key names."""
    connections = []
    try:
        user_path = f"users/{user_id}"
        agent_response = vault_client.client.secrets.kv.v1.list_secrets(
            path=user_path,
            mount_point=vault_client.mount_path
        )
        if not (agent_response and 'data' in agent_response and 'keys' in agent_response['data']):
            return connections

        for agent_folder in agent_response['data']['keys']:
            # Vault returns folder names with a trailing slash
            agent_scope = agent_folder.rstrip('/')

            is_common = (agent_scope == "COMMON")
            agent_id = None if agent_scope in ("COMMON", "default") else agent_scope

            try:
                key_response = vault_client.client.secrets.kv.v1.list_secrets(
                    path=f"{user_path}/{agent_scope}",
                    mount_point=vault_client.mount_path
                )
                if not (key_response and 'data' in key_response and 'keys' in key_response['data']):
                    continue

                for key_name in key_response['data']['keys']:
                    key_id = f"{user_id}|{key_name}|{agent_scope}"
                    connections.append(AgentConnectionResponse(
                        key_id=key_id,
                        key_name=key_name,
                        agent_id=agent_id,
                        is_common=is_common,
                        created_at=datetime.now(),
                        user_id=user_id,
                        user_name=user_info.name if user_info else None,
                        user_email=user_info.email if user_info else None,
                    ))
            except Exception as e:
                logger.debug(f"Could not list keys for {user_path}/{agent_scope}: {e}")

    except Exception as e:
        logger.debug(f"No agent connections found for user {user_id}: {e}")

    return connections


@router.get("/", response_model=List[AgentConnectionResponse])
async def list_agent_connections(user=Depends(get_verified_user)):
    """List keys for a user."""
    try:
        connections = []

        if VAULT_CONFIG.value:
            vault_client = get_vault_client()
            if vault_client and vault_client.connect():
                connections = _parse_connections_for_user(vault_client, user.id)

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
                        all_users_result = Users.get_users()
                        if hasattr(all_users_result, 'users'):
                            users_list = all_users_result.users
                        elif isinstance(all_users_result, dict) and 'users' in all_users_result:
                            users_list = all_users_result['users']
                        else:
                            users_list = all_users_result if isinstance(all_users_result, list) else []
                        all_users = {u.id: u for u in users_list}

                        for user_id in response['data']['keys']:
                            user_id = user_id.rstrip('/')
                            user_info = all_users.get(user_id)
                            connections.extend(_parse_connections_for_user(vault_client, user_id, user_info))

                except Exception as e:
                    logger.debug(f"No agent connections found: {str(e)}")
        else:
            logger.info("Vault integration disabled")

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
        # key_id format: "{user_id}|{key_name}|{agent_scope}"
        parts = key_id.split('|', 2)
        if len(parts) != 3:
            raise HTTPException(status_code=400, detail="Invalid key_id format")

        user_id_from_key, key_name, agent_scope = parts

        # Check if user has access to this key
        if user_id_from_key != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")

        # Determine if it's a common key
        is_common = (agent_scope == "COMMON")
        agent_id = None if agent_scope in ("COMMON", "default") else agent_scope
        
        # Get from vault
        if VAULT_CONFIG.value:
            value = get_agent_connection_from_vault(
                name=key_name,
                user_id=user_id_from_key,
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
        # key_id format: "{user_id}|{key_name}|{agent_scope}"
        parts = key_id.split('|', 2)
        if len(parts) != 3:
            raise HTTPException(status_code=400, detail="Invalid key_id format")

        user_id_from_key, current_key_name, agent_scope = parts

        # Check if user has access to this key
        if user_id_from_key != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")

        # Get current values if not provided in update
        is_common = (agent_scope == "COMMON")
        agent_id = None if agent_scope in ("COMMON", "default") else agent_scope
        
        # Get current value if not updating it
        current_value = None
        if not connection.key_value and VAULT_CONFIG.value:
            current_value = get_agent_connection_from_vault(
                name=current_key_name,
                user_id=user_id_from_key,
                is_common=is_common,
                agent_id=agent_id
            )
            if current_value is None:
                raise HTTPException(status_code=404, detail="Key not found")
        
        # Use provided values or current ones
        new_key_name = connection.key_name or current_key_name
        new_key_value = connection.key_value or current_value
        new_agent_id = connection.agent_id if connection.agent_id is not None else agent_id
        new_is_common = connection.is_common if connection.is_common is not None else is_common
        
        # Validate new key name if changed
        if new_key_name != current_key_name and not new_key_name.replace('_', '').isalnum():
            raise HTTPException(status_code=400, detail="Key name must be alphanumeric with underscores only")
        
        # Check if user is admin when trying to make a connection common
        if new_is_common and not is_common and user.role != "admin":
            raise HTTPException(status_code=403, detail="Only administrators can create common connections")
        
        # If key name or scope changed, delete old key first
        if (new_key_name != current_key_name or 
            new_agent_id != agent_id or 
            new_is_common != is_common):
            
            if VAULT_CONFIG.value:
                delete_agent_connection_from_vault(
                    name=current_key_name,
                    user_id=user_id_from_key,
                    is_common=is_common,
                    agent_id=agent_id
                )
        
        # Store updated connection
        vault_connection = {
            "name": new_key_name,
            "value": new_key_value,
            "agent_id": new_agent_id,
            "is_common": new_is_common
        }
        
        if VAULT_CONFIG.value:
            success = store_agent_connection_in_vault(vault_connection, user_id_from_key)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to update key in Vault")
        
        # Generate new key ID
        from open_webui.utils.vault import sanitize_agent_id as _san
        new_agent_scope = "COMMON" if new_is_common else (
            _san(new_agent_id) if new_agent_id else "default"
        )
        new_key_id = f"{user_id_from_key}|{new_key_name}|{new_agent_scope}"
        
        logger.info(f"Updated key {current_key_name} -> {new_key_name} for user {user_id_from_key}")
        
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
        # key_id format: "{user_id}|{key_name}|{agent_scope}"
        parts = key_id.split('|', 2)
        if len(parts) != 3:
            raise HTTPException(status_code=400, detail="Invalid key_id format")

        user_id_from_key, key_name, agent_scope = parts

        # Check if user has access to this key
        if user_id_from_key != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")

        # Determine scope
        is_common = (agent_scope == "COMMON")
        agent_id = None if agent_scope in ("COMMON", "default") else agent_scope
        
        # Delete from vault
        if VAULT_CONFIG.value:
            success = delete_agent_connection_from_vault(
                name=key_name,
                user_id=user_id_from_key,
                is_common=is_common,
                agent_id=agent_id
            )
            
            if not success:
                raise HTTPException(status_code=500, detail="Failed to delete key from Vault")
        
        logger.info(f"Deleted key {key_name} for user {user_id_from_key} (agent: {agent_id or 'common' if is_common else 'default'})")
        
        return {"status": "success"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting agent connection: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") 