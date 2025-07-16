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
    ENABLE_VAULT_INTEGRATION
)
from open_webui.config import ENABLE_VAULT_INTEGRATION as VAULT_CONFIG
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
        
        # Generate a key ID (using user_id + key_name + agent_id for uniqueness)
        key_id = f"{user.id}_{connection.key_name}_{connection.agent_id or ('common' if connection.is_common else 'default')}"
        
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
async def list_agent_connections(user=Depends(get_verified_user)):
    """List keys for a user."""
    try:
        connections = []
        
        if VAULT_CONFIG.value:
            # Get Vault client
            vault_client = get_vault_client()
            if vault_client and vault_client.connect():
                try:
                    # List all secrets under users/{user_id}/
                    user_path = f"users/{user.id}"
                    response = vault_client.client.secrets.kv.v1.list_secrets(
                        path=user_path,
                        mount_point=vault_client.mount_path
                    )
                    if response and 'data' in response and 'keys' in response['data']:
                        for key in response['data']['keys']:
                            # Parse the key format: {agent_name}_{key_name}
                            if '_' in key:
                                parts = key.split('_', 1)
                                if len(parts) == 2:
                                    agent_scope, key_name = parts
                                    
                                    # Determine if it's common, default, or specific agent
                                    is_common = agent_scope == "common"
                                    agent_id = None if agent_scope in ["common", "default"] else agent_scope
                                    
                                    # Generate key_id for consistency
                                    key_id = f"{user.id}_{key_name}_{agent_scope}"
                                    
                                    connections.append(AgentConnectionResponse(
                                        key_id=key_id,
                                        key_name=key_name,
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


@router.get("/{key_id}", response_model=dict)
async def get_agent_connection(
    key_id: str,
    user=Depends(get_verified_user)
):
    """Get a specific agent connection by key_id."""
    try:
        # Parse key_id to extract components
        # Format: user_id_key_name_agent_or_scope
        parts = key_id.split('_', 3)
        if len(parts) < 3:
            raise HTTPException(status_code=400, detail="Invalid key_id format")
        
        user_id_from_key = parts[0]
        key_name = parts[1]
        agent_scope = parts[2] if len(parts) > 2 else "default"
        
        # Check if user has access to this key
        if user_id_from_key != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Determine if it's a common key
        is_common = agent_scope == "common"
        agent_id = None if is_common or agent_scope == "default" else agent_scope
        
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
        # Parse key_id to extract components
        parts = key_id.split('_', 3)
        if len(parts) < 3:
            raise HTTPException(status_code=400, detail="Invalid key_id format")
        
        user_id_from_key = parts[0]
        current_key_name = parts[1]
        agent_scope = parts[2] if len(parts) > 2 else "default"
        
        # Check if user has access to this key
        if user_id_from_key != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get current values if not provided in update
        is_common = agent_scope == "common"
        agent_id = None if is_common or agent_scope == "default" else agent_scope
        
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
        new_key_id = f"{user_id_from_key}_{new_key_name}_{new_agent_id or ('common' if new_is_common else 'default')}"
        
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
        # Parse key_id to extract components
        parts = key_id.split('_', 3)
        if len(parts) < 3:
            raise HTTPException(status_code=400, detail="Invalid key_id format")
        
        user_id_from_key = parts[0]
        key_name = parts[1]
        agent_scope = parts[2] if len(parts) > 2 else "default"
        
        # Check if user has access to this key
        if user_id_from_key != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Determine scope
        is_common = agent_scope == "common"
        agent_id = None if is_common or agent_scope == "default" else agent_scope
        
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