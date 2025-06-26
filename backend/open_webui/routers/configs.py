from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, ConfigDict

from typing import Optional, List, Dict, Any

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.config import get_config, save_config
from open_webui.config import BannerModel
from open_webui.config import ENABLE_VAULT_INTEGRATION, VAULT_URL, VAULT_TOKEN, VAULT_MOUNT_PATH, VAULT_VERSION, VAULT_TIMEOUT, VAULT_VERIFY_SSL

from open_webui.utils.tools import get_tool_server_data, get_tool_servers_data
from open_webui.utils.vault import test_vault_connection, store_agent_connection_in_vault, get_agent_connection_from_vault, delete_agent_connection_from_vault
from loguru import logger


router = APIRouter()


############################
# ImportConfig
############################


class ImportConfigForm(BaseModel):
    config: dict


@router.post("/import", response_model=dict)
async def import_config(form_data: ImportConfigForm, user=Depends(get_admin_user)):
    save_config(form_data.config)
    return get_config()


############################
# ExportConfig
############################


@router.get("/export", response_model=dict)
async def export_config(user=Depends(get_admin_user)):
    return get_config()


############################
# Direct Connections Config
############################


class DirectConnectionsConfigForm(BaseModel):
    ENABLE_DIRECT_CONNECTIONS: bool


@router.get("/direct_connections", response_model=DirectConnectionsConfigForm)
async def get_direct_connections_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_DIRECT_CONNECTIONS": request.app.state.config.ENABLE_DIRECT_CONNECTIONS,
    }


@router.post("/direct_connections", response_model=DirectConnectionsConfigForm)
async def set_direct_connections_config(
    request: Request,
    form_data: DirectConnectionsConfigForm,
    user=Depends(get_admin_user),
):
    request.app.state.config.ENABLE_DIRECT_CONNECTIONS = (
        form_data.ENABLE_DIRECT_CONNECTIONS
    )
    return {
        "ENABLE_DIRECT_CONNECTIONS": request.app.state.config.ENABLE_DIRECT_CONNECTIONS,
    }


############################
# ToolServers Config
############################


class ToolServerConnection(BaseModel):
    url: str
    path: str
    auth_type: Optional[str]
    key: Optional[str]
    config: Optional[dict]

    model_config = ConfigDict(extra="allow")


class ToolServersConfigForm(BaseModel):
    TOOL_SERVER_CONNECTIONS: list[ToolServerConnection]


@router.get("/tool_servers", response_model=ToolServersConfigForm)
async def get_tool_servers_config(request: Request, user=Depends(get_admin_user)):
    return {
        "TOOL_SERVER_CONNECTIONS": request.app.state.config.TOOL_SERVER_CONNECTIONS,
    }


@router.post("/tool_servers", response_model=ToolServersConfigForm)
async def set_tool_servers_config(
    request: Request,
    form_data: ToolServersConfigForm,
    user=Depends(get_admin_user),
):
    request.app.state.config.TOOL_SERVER_CONNECTIONS = [
        connection.model_dump() for connection in form_data.TOOL_SERVER_CONNECTIONS
    ]

    request.app.state.TOOL_SERVERS = await get_tool_servers_data(
        request.app.state.config.TOOL_SERVER_CONNECTIONS
    )

    return {
        "TOOL_SERVER_CONNECTIONS": request.app.state.config.TOOL_SERVER_CONNECTIONS,
    }


@router.post("/tool_servers/verify")
async def verify_tool_servers_config(
    request: Request, form_data: ToolServerConnection, user=Depends(get_admin_user)
):
    """
    Verify the connection to the tool server.
    """
    try:

        token = None
        if form_data.auth_type == "bearer":
            token = form_data.key
        elif form_data.auth_type == "session":
            token = request.state.token.credentials

        url = f"{form_data.url}/{form_data.path}"
        return await get_tool_server_data(token, url)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect to the tool server: {str(e)}",
        )


############################
# Agent Connections Config
############################

class AgentConnection(BaseModel):
    name: str
    value: str
    agent_id: Optional[str] = None
    is_common: bool = False
    
    model_config = ConfigDict(extra="allow")


class AgentConnectionsConfigForm(BaseModel):
    AGENT_CONNECTIONS: List[AgentConnection] = []


class VaultConfigForm(BaseModel):
    ENABLE_VAULT_INTEGRATION: bool
    VAULT_URL: str
    VAULT_TOKEN: str
    VAULT_MOUNT_PATH: str
    VAULT_VERSION: int
    VAULT_TIMEOUT: int
    VAULT_VERIFY_SSL: bool


@router.get("/agent_connections", response_model=AgentConnectionsConfigForm)
async def get_agent_connections_config(request: Request, user=Depends(get_verified_user)):
    # Admin users can see all connections
    if user.role == "admin":
        # Handle case where AGENT_CONNECTIONS might be a list instead of PersistentConfig
        agent_connections = request.app.state.config.AGENT_CONNECTIONS
        if hasattr(agent_connections, 'value'):
            connections = agent_connections.value
        else:
            # If it's already a list, use it directly
            connections = agent_connections if isinstance(agent_connections, list) else []
        
        # If Vault integration is enabled, fetch secrets from Vault
        if ENABLE_VAULT_INTEGRATION.value:
            updated_connections = []
            for conn in connections:
                # Try to get the value from Vault
                vault_value = get_agent_connection_from_vault(
                    name=conn.get("name"),
                    user_id=user.id,
                    is_common=conn.get("is_common", False),
                    agent_id=conn.get("agent_id")
                )
                
                # If found in Vault, use that value
                if vault_value is not None:
                    conn_copy = dict(conn)
                    conn_copy["value"] = vault_value
                    updated_connections.append(conn_copy)
                else:
                    updated_connections.append(conn)
            
            return {"AGENT_CONNECTIONS": updated_connections}
        
        return {"AGENT_CONNECTIONS": connections}
    
    # Regular users can only see common connections or ones associated with their agents
    # Check if user has agents property
    user_agents = getattr(user, 'agents', [])
    
    # Handle case where AGENT_CONNECTIONS might be a list instead of PersistentConfig
    agent_connections = request.app.state.config.AGENT_CONNECTIONS
    if hasattr(agent_connections, 'value'):
        all_connections = agent_connections.value
    else:
        all_connections = agent_connections if isinstance(agent_connections, list) else []
    
    user_connections = [
        conn for conn in all_connections
        if conn.get("is_common", False) or (conn.get("agent_id") and conn.get("agent_id") in user_agents)
    ]
    
    # If Vault integration is enabled, fetch secrets from Vault
    if ENABLE_VAULT_INTEGRATION.value:
        updated_connections = []
        for conn in user_connections:
            # Try to get the value from Vault
            vault_value = get_agent_connection_from_vault(
                name=conn.get("name"),
                user_id=user.id,
                is_common=conn.get("is_common", False),
                agent_id=conn.get("agent_id")
            )
            
            # If found in Vault, use that value
            if vault_value is not None:
                conn_copy = dict(conn)
                conn_copy["value"] = vault_value
                updated_connections.append(conn_copy)
            else:
                updated_connections.append(conn)
        
        return {"AGENT_CONNECTIONS": updated_connections}
    
    return {"AGENT_CONNECTIONS": user_connections}


@router.post("/agent_connections", response_model=AgentConnectionsConfigForm)
async def set_agent_connections_config(
    request: Request,
    form_data: AgentConnectionsConfigForm,
    user=Depends(get_admin_user),
):
    connections = [connection.model_dump() for connection in form_data.AGENT_CONNECTIONS]
    
    # If Vault integration is enabled, store secrets in Vault
    if ENABLE_VAULT_INTEGRATION.value:
        for connection in connections:
            # Store the secret in Vault
            success = store_agent_connection_in_vault(connection, user.id)
            
            # If successfully stored in Vault, remove the value from the connection
            # to avoid storing it in the database
            if success:
                # Keep a placeholder value to indicate it's stored in Vault
                connection["value"] = "[STORED_IN_VAULT]"
                logger.info(f"Stored agent connection {connection.get('name')} for user {user.id} in Vault")
            else:
                logger.error(f"Failed to store agent connection {connection.get('name')} for user {user.id} in Vault")
    
    # Update the PersistentConfig value (or set directly if it's a list)
    agent_connections = request.app.state.config.AGENT_CONNECTIONS
    if hasattr(agent_connections, 'value'):
        agent_connections.value = connections
    else:
        # If it's not a PersistentConfig, set it directly
        request.app.state.config.AGENT_CONNECTIONS = connections
    
    # Return the current value
    if hasattr(request.app.state.config.AGENT_CONNECTIONS, 'value'):
        return {"AGENT_CONNECTIONS": request.app.state.config.AGENT_CONNECTIONS.value}
    else:
        return {"AGENT_CONNECTIONS": request.app.state.config.AGENT_CONNECTIONS}


@router.get("/agent_connections/vault_config", response_model=VaultConfigForm)
async def get_vault_config(request: Request, user=Depends(get_admin_user)):
    """Get the Vault configuration."""
    return {
        "ENABLE_VAULT_INTEGRATION": ENABLE_VAULT_INTEGRATION.value,
        "VAULT_URL": VAULT_URL.value,
        "VAULT_TOKEN": VAULT_TOKEN.value,
        "VAULT_MOUNT_PATH": VAULT_MOUNT_PATH.value,
        "VAULT_VERSION": VAULT_VERSION.value,
        "VAULT_TIMEOUT": VAULT_TIMEOUT.value,
        "VAULT_VERIFY_SSL": VAULT_VERIFY_SSL.value,
    }


@router.post("/agent_connections/vault_config", response_model=VaultConfigForm)
async def set_vault_config(
    request: Request,
    form_data: VaultConfigForm,
    user=Depends(get_admin_user),
):
    """Set the Vault configuration."""
    ENABLE_VAULT_INTEGRATION.value = form_data.ENABLE_VAULT_INTEGRATION
    VAULT_URL.value = form_data.VAULT_URL
    VAULT_TOKEN.value = form_data.VAULT_TOKEN
    VAULT_MOUNT_PATH.value = form_data.VAULT_MOUNT_PATH
    VAULT_VERSION.value = form_data.VAULT_VERSION
    VAULT_TIMEOUT.value = form_data.VAULT_TIMEOUT
    VAULT_VERIFY_SSL.value = form_data.VAULT_VERIFY_SSL
    
    return {
        "ENABLE_VAULT_INTEGRATION": ENABLE_VAULT_INTEGRATION.value,
        "VAULT_URL": VAULT_URL.value,
        "VAULT_TOKEN": VAULT_TOKEN.value,
        "VAULT_MOUNT_PATH": VAULT_MOUNT_PATH.value,
        "VAULT_VERSION": VAULT_VERSION.value,
        "VAULT_TIMEOUT": VAULT_TIMEOUT.value,
        "VAULT_VERIFY_SSL": VAULT_VERIFY_SSL.value,
    }


@router.post("/agent_connections/test_vault_connection")
async def test_vault_connection_endpoint(
    request: Request,
    form_data: VaultConfigForm,
    user=Depends(get_admin_user),
):
    """Test the connection to Vault."""
    success, message = test_vault_connection(
        url=form_data.VAULT_URL,
        token=form_data.VAULT_TOKEN,
        mount_path=form_data.VAULT_MOUNT_PATH,
        kv_version=form_data.VAULT_VERSION,
        timeout=form_data.VAULT_TIMEOUT,
        verify_ssl=form_data.VAULT_VERIFY_SSL
    )
    
    if success:
        return {"status": "success", "message": message}
    else:
        raise HTTPException(status_code=400, detail=message)


############################
# CodeInterpreterConfig
############################
class CodeInterpreterConfigForm(BaseModel):
    ENABLE_CODE_EXECUTION: bool
    CODE_EXECUTION_ENGINE: str
    CODE_EXECUTION_JUPYTER_URL: Optional[str]
    CODE_EXECUTION_JUPYTER_AUTH: Optional[str]
    CODE_EXECUTION_JUPYTER_AUTH_TOKEN: Optional[str]
    CODE_EXECUTION_JUPYTER_AUTH_PASSWORD: Optional[str]
    CODE_EXECUTION_JUPYTER_TIMEOUT: Optional[int]
    ENABLE_CODE_INTERPRETER: bool
    CODE_INTERPRETER_ENGINE: str
    CODE_INTERPRETER_PROMPT_TEMPLATE: Optional[str]
    CODE_INTERPRETER_JUPYTER_URL: Optional[str]
    CODE_INTERPRETER_JUPYTER_AUTH: Optional[str]
    CODE_INTERPRETER_JUPYTER_AUTH_TOKEN: Optional[str]
    CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD: Optional[str]
    CODE_INTERPRETER_JUPYTER_TIMEOUT: Optional[int]


@router.get("/code_execution", response_model=CodeInterpreterConfigForm)
async def get_code_execution_config(request: Request, user=Depends(get_admin_user)):
    return {
        "ENABLE_CODE_EXECUTION": request.app.state.config.ENABLE_CODE_EXECUTION,
        "CODE_EXECUTION_ENGINE": request.app.state.config.CODE_EXECUTION_ENGINE,
        "CODE_EXECUTION_JUPYTER_URL": request.app.state.config.CODE_EXECUTION_JUPYTER_URL,
        "CODE_EXECUTION_JUPYTER_AUTH": request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH,
        "CODE_EXECUTION_JUPYTER_AUTH_TOKEN": request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_TOKEN,
        "CODE_EXECUTION_JUPYTER_AUTH_PASSWORD": request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD,
        "CODE_EXECUTION_JUPYTER_TIMEOUT": request.app.state.config.CODE_EXECUTION_JUPYTER_TIMEOUT,
        "ENABLE_CODE_INTERPRETER": request.app.state.config.ENABLE_CODE_INTERPRETER,
        "CODE_INTERPRETER_ENGINE": request.app.state.config.CODE_INTERPRETER_ENGINE,
        "CODE_INTERPRETER_PROMPT_TEMPLATE": request.app.state.config.CODE_INTERPRETER_PROMPT_TEMPLATE,
        "CODE_INTERPRETER_JUPYTER_URL": request.app.state.config.CODE_INTERPRETER_JUPYTER_URL,
        "CODE_INTERPRETER_JUPYTER_AUTH": request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH,
        "CODE_INTERPRETER_JUPYTER_AUTH_TOKEN": request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN,
        "CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD": request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD,
        "CODE_INTERPRETER_JUPYTER_TIMEOUT": request.app.state.config.CODE_INTERPRETER_JUPYTER_TIMEOUT,
    }


@router.post("/code_execution", response_model=CodeInterpreterConfigForm)
async def set_code_execution_config(
    request: Request, form_data: CodeInterpreterConfigForm, user=Depends(get_admin_user)
):

    request.app.state.config.ENABLE_CODE_EXECUTION = form_data.ENABLE_CODE_EXECUTION

    request.app.state.config.CODE_EXECUTION_ENGINE = form_data.CODE_EXECUTION_ENGINE
    request.app.state.config.CODE_EXECUTION_JUPYTER_URL = (
        form_data.CODE_EXECUTION_JUPYTER_URL
    )
    request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH = (
        form_data.CODE_EXECUTION_JUPYTER_AUTH
    )
    request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_TOKEN = (
        form_data.CODE_EXECUTION_JUPYTER_AUTH_TOKEN
    )
    request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD = (
        form_data.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD
    )
    request.app.state.config.CODE_EXECUTION_JUPYTER_TIMEOUT = (
        form_data.CODE_EXECUTION_JUPYTER_TIMEOUT
    )

    request.app.state.config.ENABLE_CODE_INTERPRETER = form_data.ENABLE_CODE_INTERPRETER
    request.app.state.config.CODE_INTERPRETER_ENGINE = form_data.CODE_INTERPRETER_ENGINE
    request.app.state.config.CODE_INTERPRETER_PROMPT_TEMPLATE = (
        form_data.CODE_INTERPRETER_PROMPT_TEMPLATE
    )

    request.app.state.config.CODE_INTERPRETER_JUPYTER_URL = (
        form_data.CODE_INTERPRETER_JUPYTER_URL
    )

    request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH = (
        form_data.CODE_INTERPRETER_JUPYTER_AUTH
    )

    request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN = (
        form_data.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN
    )
    request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD = (
        form_data.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD
    )
    request.app.state.config.CODE_INTERPRETER_JUPYTER_TIMEOUT = (
        form_data.CODE_INTERPRETER_JUPYTER_TIMEOUT
    )

    return {
        "ENABLE_CODE_EXECUTION": request.app.state.config.ENABLE_CODE_EXECUTION,
        "CODE_EXECUTION_ENGINE": request.app.state.config.CODE_EXECUTION_ENGINE,
        "CODE_EXECUTION_JUPYTER_URL": request.app.state.config.CODE_EXECUTION_JUPYTER_URL,
        "CODE_EXECUTION_JUPYTER_AUTH": request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH,
        "CODE_EXECUTION_JUPYTER_AUTH_TOKEN": request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_TOKEN,
        "CODE_EXECUTION_JUPYTER_AUTH_PASSWORD": request.app.state.config.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD,
        "CODE_EXECUTION_JUPYTER_TIMEOUT": request.app.state.config.CODE_EXECUTION_JUPYTER_TIMEOUT,
        "ENABLE_CODE_INTERPRETER": request.app.state.config.ENABLE_CODE_INTERPRETER,
        "CODE_INTERPRETER_ENGINE": request.app.state.config.CODE_INTERPRETER_ENGINE,
        "CODE_INTERPRETER_PROMPT_TEMPLATE": request.app.state.config.CODE_INTERPRETER_PROMPT_TEMPLATE,
        "CODE_INTERPRETER_JUPYTER_URL": request.app.state.config.CODE_INTERPRETER_JUPYTER_URL,
        "CODE_INTERPRETER_JUPYTER_AUTH": request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH,
        "CODE_INTERPRETER_JUPYTER_AUTH_TOKEN": request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN,
        "CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD": request.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD,
        "CODE_INTERPRETER_JUPYTER_TIMEOUT": request.app.state.config.CODE_INTERPRETER_JUPYTER_TIMEOUT,
    }


############################
# SetDefaultModels
############################
class ModelsConfigForm(BaseModel):
    DEFAULT_MODELS: Optional[str]
    MODEL_ORDER_LIST: Optional[list[str]]


@router.get("/models", response_model=ModelsConfigForm)
async def get_models_config(request: Request, user=Depends(get_admin_user)):
    return {
        "DEFAULT_MODELS": request.app.state.config.DEFAULT_MODELS,
        "MODEL_ORDER_LIST": request.app.state.config.MODEL_ORDER_LIST,
    }


@router.post("/models", response_model=ModelsConfigForm)
async def set_models_config(
    request: Request, form_data: ModelsConfigForm, user=Depends(get_admin_user)
):
    request.app.state.config.DEFAULT_MODELS = form_data.DEFAULT_MODELS
    request.app.state.config.MODEL_ORDER_LIST = form_data.MODEL_ORDER_LIST
    return {
        "DEFAULT_MODELS": request.app.state.config.DEFAULT_MODELS,
        "MODEL_ORDER_LIST": request.app.state.config.MODEL_ORDER_LIST,
    }


class PromptSuggestion(BaseModel):
    title: list[str]
    content: str


class SetDefaultSuggestionsForm(BaseModel):
    suggestions: list[PromptSuggestion]


@router.post("/suggestions", response_model=list[PromptSuggestion])
async def set_default_suggestions(
    request: Request,
    form_data: SetDefaultSuggestionsForm,
    user=Depends(get_admin_user),
):
    data = form_data.model_dump()
    request.app.state.config.DEFAULT_PROMPT_SUGGESTIONS = data["suggestions"]
    return request.app.state.config.DEFAULT_PROMPT_SUGGESTIONS


############################
# SetBanners
############################


class SetBannersForm(BaseModel):
    banners: list[BannerModel]


@router.post("/banners", response_model=list[BannerModel])
async def set_banners(
    request: Request,
    form_data: SetBannersForm,
    user=Depends(get_admin_user),
):
    data = form_data.model_dump()
    request.app.state.config.BANNERS = data["banners"]
    return request.app.state.config.BANNERS


@router.get("/banners", response_model=list[BannerModel])
async def get_banners(
    request: Request,
    user=Depends(get_verified_user),
):
    return request.app.state.config.BANNERS
