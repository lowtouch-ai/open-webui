from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
 

from open_webui.utils.auth import get_verified_user, get_admin_user
from open_webui.utils.vault import (
    store_agent_connection_in_vault,
    get_agent_connection_from_vault,
    delete_agent_connection_from_vault,
    get_vault_client,
    sanitize_agent_name,
    sanitize_key_field,
)
from open_webui.config import ENABLE_VAULT_INTEGRATION as VAULT_CONFIG
from open_webui.models.users import Users
from loguru import logger

router = APIRouter()


def _parse_requested_items(raw_keys: Optional[str]) -> Optional[set[str]]:
    """Return a set of slash-formatted header items from X-LTAI-Vault-Keys.

    Accepted formats only:
      - "COMMON/<key_name>"
      - "<agent_scope>/<key_name>" where agent_scope is underscore-normalized
    """
    if not raw_keys:
        return None
    items = {k.strip() for k in raw_keys.split(',') if k.strip() and '/' in k}
    return items if items else None


def _is_requested_key(key_name: str, agent_scope: str, requested_items: Optional[set[str]]) -> bool:
    """Decide if a given Vault field key_name should be included for a specific agent scope.

    Only slash-formatted items are supported: "<scope>/<key>". The key portion may contain slashes.
    Scope must match the current agent_scope ("common", "default", or underscore-normalized agent name).
    Key name is compared against the SANITIZED header key (slashes/backslashes -> underscore),
    because fields are stored sanitized in Vault.
    """
    if not requested_items:
        return True
    for item in requested_items:
        if "/" not in item:
            continue
        scope_part, key_part = item.split("/", 1)
        # Map "COMMON" header scope to stored path scope "common"
        header_scope = "common" if scope_part == "COMMON" else scope_part
        # Sanitize the key part to match stored field names
        if header_scope == agent_scope.lower() and key_name == sanitize_key_field(key_part):
            return True
    return False


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
    request: Request,
    user=Depends(get_verified_user)
):
    """Create or update a key in Vault."""
    try:
        # Validate input
        if not connection.key_name or not connection.key_value:
            raise HTTPException(status_code=400, detail="Key name and value are required")
        
        # Prepare connection data for vault
        vault_connection = {
            "name": connection.key_name,
            "value": connection.key_value,
            "agent_id": connection.agent_id,
            "is_common": connection.is_common
        }
        
        # Store in vault if enabled
        vault_user_id = request.headers.get('x-ltai-vault-user') or user.id
        if VAULT_CONFIG.value:
            success = store_agent_connection_in_vault(vault_connection, vault_user_id)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to store key in Vault")
        
        # Log the operation
        logger.info(f"Stored key {connection.key_name} for user {vault_user_id} (agent: {connection.agent_id or 'common' if connection.is_common else 'default'})")
        
        # Generate a path-safe key ID using normalized underscore agent scope
        scope_for_id = (
            'common' if connection.is_common else (
                'default' if not connection.agent_id else sanitize_agent_name(connection.agent_id)
            )
        )
        # Use sanitized key name in key_id for consistency with stored field names
        key_id = f"{vault_user_id}_{sanitize_key_field(connection.key_name)}_{scope_for_id}"
        
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


@router.get("/", response_model=List[AgentConnectionResponse])
async def list_agent_connections(request: Request, user=Depends(get_verified_user)):
    """List keys for a user."""
    try:
        connections = []
        
        if VAULT_CONFIG.value:
            # Get Vault client
            vault_client = get_vault_client()
            if vault_client and vault_client.connect():
                try:
                    # Determine target vault user and requested keys
                    vault_user_id = request.headers.get('x-ltai-vault-user') or user.id
                    raw_keys = request.headers.get('x-ltai-vault-keys')
                    requested_items = _parse_requested_items(raw_keys)

                    # List agent scopes under users/{vault_user_id}/ (each key is an agent_name)
                    user_path = f"users/{vault_user_id}"
                    response = vault_client.client.secrets.kv.v1.list_secrets(
                        path=user_path,
                        mount_point=vault_client.mount_path
                    )
                    if response and 'data' in response and 'keys' in response['data']:
                        for agent_scope in response['data']['keys']:
                            # Remove trailing slash if any
                            agent_scope = agent_scope[:-1] if agent_scope.endswith('/') else agent_scope
                            agent_scope_decoded = agent_scope.lower()
                            # Read secret at users/{user_id}/{agent_scope} to get fields (use original casing from Vault)
                            secret_path = f"users/{vault_user_id}/{agent_scope}"
                            secret = vault_client.client.secrets.kv.v1.read_secret(
                                path=secret_path,
                                mount_point=vault_client.mount_path
                            )
                            data = secret.get('data') if secret else None
                            if data:
                                for key_name in data.keys():
                                    # Use raw field name (no URL decoding)
                                    decoded_key_name = key_name
                                    if requested_items and not _is_requested_key(decoded_key_name, agent_scope_decoded, requested_items):
                                        continue
                                    is_common = agent_scope_decoded == "common"
                                    agent_id = None if agent_scope_decoded in ["common", "default"] else agent_scope_decoded
                                    # Use lowercase scope for key_id for consistency
                                    key_id = f"{vault_user_id}_{decoded_key_name}_{agent_scope_decoded}"
                                    connections.append(AgentConnectionResponse(
                                        key_id=key_id,
                                        key_name=decoded_key_name,
                                        agent_id=agent_id,
                                        is_common=is_common,
                                        created_at=datetime.now()  # We don't have actual creation time from Vault
                                    ))
                except Exception as e:
                    # If listing fails (e.g., path doesn't exist), just return empty list
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
            # Get Vault client
            vault_client = get_vault_client()
            if vault_client and vault_client.connect():
                try:
                    # Get all user information once from the database.
                    # Users.get_users() returns a dict {"users": [...], "total": N}
                    users_result = Users.get_users()
                    user_list = users_result.get("users", []) if isinstance(users_result, dict) else []
                    all_users = {u.id: u for u in user_list}

                    # Iterate over known users instead of listing the Vault root "users" path,
                    # which may not be allowed by all Vault policies.
                    for user_id, user_info in all_users.items():
                        try:
                            # List agent scopes for this user
                            user_response = vault_client.client.secrets.kv.v1.list_secrets(
                                path=f"users/{user_id}",
                                mount_point=vault_client.mount_path
                            )

                            if user_response and 'data' in user_response and 'keys' in user_response['data']:
                                for agent_scope in user_response['data']['keys']:
                                    agent_scope = agent_scope[:-1] if agent_scope.endswith('/') else agent_scope
                                    agent_scope_decoded = agent_scope.lower()
                                    secret_path = f"users/{user_id}/{agent_scope}"
                                    secret = vault_client.client.secrets.kv.v1.read_secret(
                                        path=secret_path,
                                        mount_point=vault_client.mount_path
                                    )
                                    data = secret.get('data') if secret else None
                                    if data:
                                        for key_name in data.keys():
                                            decoded_key_name = key_name
                                            is_common = agent_scope_decoded == "common"
                                            agent_id = None if agent_scope_decoded in ["common", "default"] else agent_scope_decoded
                                            # Use lowercase scope for key_id for consistency
                                            key_id = f"{user_id}_{decoded_key_name}_{agent_scope_decoded}"
                                            connections.append(AgentConnectionResponse(
                                                key_id=key_id,
                                                key_name=decoded_key_name,
                                                agent_id=agent_id,
                                                is_common=is_common,
                                                created_at=datetime.now(),  # We don't have actual creation time from Vault
                                                user_id=user_id,
                                                user_name=user_info.name if user_info else None,
                                                user_email=user_info.email if user_info else None
                                            ))
                        except Exception as e:
                            # If listing fails for a user, just skip them
                            logger.debug(f"No agent connections found for user {user_id}: {str(e)}")

                except Exception as e:
                    # If listing fails, just return empty list
                    logger.debug(f"No agent connections found: {str(e)}")

        logger.info(f"Admin listed {len(connections)} agent connections from all users")

        return connections

    except Exception as e:
        logger.error(f"Error listing all agent connections: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{key_id:path}", response_model=dict)
async def get_agent_connection(
    key_id: str,
    request: Request,
    user=Depends(get_verified_user)
):
    """Get a specific agent connection by key_id."""
    try:
        # Parse key_id to extract components
        # Format: user_id_key_name_agent_or_scope (key_name can contain underscores)
        first_sep = key_id.find('_')
        last_sep = key_id.rfind('_')
        if first_sep == -1 or last_sep == -1 or last_sep <= first_sep:
            raise HTTPException(status_code=400, detail="Invalid key_id format")
        user_id_from_key = key_id[:first_sep]
        agent_scope = key_id[last_sep+1:]
        agent_scope_decoded = agent_scope
        key_name = key_id[first_sep+1:last_sep]
        if not key_name:
            raise HTTPException(status_code=400, detail="Invalid key_id format")
        
        # Check if user has access to this key
        if user_id_from_key != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Determine if it's a common key
        is_common = agent_scope_decoded == "common"
        agent_id = None if is_common or agent_scope_decoded == "default" else agent_scope_decoded
        
        # Get from vault
        if VAULT_CONFIG.value:
            value = get_agent_connection_from_vault(
                name=key_name,
                user_id=request.headers.get('x-ltai-vault-user') or user_id_from_key,
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


@router.put("/{key_id:path}", response_model=AgentConnectionResponse)
async def update_agent_connection(
    key_id: str,
    connection: AgentConnectionUpdate,
    request: Request,
    user=Depends(get_verified_user)
):
    """Update an existing agent connection."""
    try:
        # Parse key_id to extract components
        first_sep = key_id.find('_')
        last_sep = key_id.rfind('_')
        if first_sep == -1 or last_sep == -1 or last_sep <= first_sep:
            raise HTTPException(status_code=400, detail="Invalid key_id format")
        user_id_from_key = key_id[:first_sep]
        agent_scope = key_id[last_sep+1:]
        agent_scope_decoded = agent_scope
        current_key_name = key_id[first_sep+1:last_sep]
        if not current_key_name:
            raise HTTPException(status_code=400, detail="Invalid key_id format")
        
        # Check if user has access to this key
        if user_id_from_key != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get current values if not provided in update
        is_common = agent_scope_decoded == "common"
        agent_id = None if is_common or agent_scope_decoded == "default" else agent_scope_decoded
        
        # Get current value if not updating it
        current_value = None
        if not connection.key_value and VAULT_CONFIG.value:
            current_value = get_agent_connection_from_vault(
                name=current_key_name,
                user_id=request.headers.get('x-ltai-vault-user') or user_id_from_key,
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
        
        # No strict validation on key names; allow arbitrary strings

        # If key name or scope changed, delete old key first
        if (new_key_name != current_key_name or 
            new_agent_id != agent_id or 
            new_is_common != is_common):
            
            if VAULT_CONFIG.value:
                delete_agent_connection_from_vault(
                    name=current_key_name,
                    user_id=request.headers.get('x-ltai-vault-user') or user_id_from_key,
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
            vault_user_id = request.headers.get('x-ltai-vault-user') or user_id_from_key
            success = store_agent_connection_in_vault(vault_connection, vault_user_id)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to update key in Vault")
        
        # Generate new key ID with encoded scope to be path-safe
        new_scope_for_id = (
            'common' if new_is_common else (
                'default' if not new_agent_id else sanitize_agent_name(new_agent_id)
            )
        )
        new_key_id = f"{user_id_from_key}_{sanitize_key_field(new_key_name)}_{new_scope_for_id}"
        
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


@router.delete("/{key_id:path}", response_model=dict)
async def delete_agent_connection(
    key_id: str,
    request: Request,
    user=Depends(get_verified_user)
):
    """Delete a key from Vault."""
    try:
        # Parse key_id to extract components
        first_sep = key_id.find('_')
        last_sep = key_id.rfind('_')
        if first_sep == -1 or last_sep == -1 or last_sep <= first_sep:
            raise HTTPException(status_code=400, detail="Invalid key_id format")
        user_id_from_key = key_id[:first_sep]
        agent_scope = key_id[last_sep+1:]
        agent_scope_decoded = agent_scope
        key_name = key_id[first_sep+1:last_sep]
        if not key_name:
            raise HTTPException(status_code=400, detail="Invalid key_id format")
        
        # Check if user has access to this key
        if user_id_from_key != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Determine scope
        is_common = agent_scope_decoded == "common"
        agent_id = None if is_common or agent_scope_decoded == "default" else agent_scope_decoded
        
        # Delete from vault
        if VAULT_CONFIG.value:
            success = delete_agent_connection_from_vault(
                name=key_name,
                user_id=request.headers.get('x-ltai-vault-user') or user_id_from_key,
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