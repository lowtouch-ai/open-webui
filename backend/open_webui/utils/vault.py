"""
HashiCorp Vault integration for Open WebUI.

This module provides functionality to securely store and retrieve agent connection
secrets in HashiCorp Vault instead of the local database.
"""

import os
import re
from typing import Dict, Any, Optional, List, Tuple

import hvac
from hvac.exceptions import VaultError, InvalidPath
from loguru import logger

# Environment variable configuration
VAULT_URL = os.environ.get("VAULT_URL", "http://localhost:8200")
VAULT_TOKEN = os.environ.get("VAULT_TOKEN", "")
VAULT_MOUNT_PATH = os.environ.get("VAULT_MOUNT_PATH", "secret")
VAULT_VERSION = int(os.environ.get("VAULT_VERSION", "1"))
ENABLE_VAULT_INTEGRATION = os.environ.get("ENABLE_VAULT_INTEGRATION", "false").lower() == "true"
VAULT_TIMEOUT = int(os.environ.get("VAULT_TIMEOUT", "30"))
VAULT_VERIFY_SSL = os.environ.get("VAULT_VERIFY_SSL", "true").lower() == "true"
# NOTE: Values are stored in Vault as-is; no additional application-level encryption.


def sanitize_agent_name(agent_identifier: Optional[str]) -> str:
    """Normalize an agent/model identifier to an underscore-safe name.

    Rule:
      - If the identifier contains a colon, take the substring BEFORE the first colon.
      - Replace all non-alphanumeric characters with underscores ('_').
      - Collapse consecutive non-alphanumerics into a single underscore.
      - Trim leading/trailing underscores.
      - If result is empty, fall back to "default".

    Examples:
      - "webshop-email:0.5" -> "webshop_email"
      - "webshop/hr:0.3" -> "webshop_hr"
      - "webshop@special#chars:1.0" -> "webshop_special_chars"

    Args:
        agent_identifier: The agent/model identifier string.

    Returns:
        str: Underscore-normalized agent name suitable as a single path segment.
    """
    if not agent_identifier:
        return "default"
    ident = str(agent_identifier)
    # Take part before the first ':' if present
    if ":" in ident:
        ident = ident.split(":", 1)[0]
    # Replace any run of non-alphanumeric chars with a single underscore
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", ident).strip("_")
    return normalized if normalized else "default"


def sanitize_key_field(key: str) -> str:
    """Sanitize a secret field (key name) to avoid path separator issues.

    - Replace '/' and '\\' with '_'.
    - Leave other characters as-is to preserve user-friendly names.
    """
    if key is None:
        return key
    return key.replace("/", "_").replace("\\", "_")


class VaultClient:
    """Client for interacting with HashiCorp Vault."""
    
    def __init__(
        self,
        url: str = VAULT_URL,
        token: str = VAULT_TOKEN,
        mount_path: str = VAULT_MOUNT_PATH,
        kv_version: int = VAULT_VERSION,
        timeout: int = VAULT_TIMEOUT,
        verify_ssl: bool = VAULT_VERIFY_SSL
    ):
        """Initialize the Vault client.
        
        Args:
            url: Vault server URL
            token: Vault authentication token
            mount_path: Mount path for the KV secrets engine
            kv_version: KV secrets engine version (1)
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        self.url = url
        self.token = token
        self.mount_path = mount_path
        self.kv_version = kv_version
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.client = None
        
        # Validate KV version
        if self.kv_version != 1:
            raise ValueError("KV version must be 1")
    
    def connect(self) -> bool:
        """Connect to Vault server and verify authentication.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            self.client = hvac.Client(
                url=self.url,
                token=self.token,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            
            # Check if client is authenticated
            if not self.client.is_authenticated():
                logger.error("Failed to authenticate with Vault")
                return False
                
            # Check if KV secrets engine is mounted
            mounted_engines = self.client.sys.list_mounted_secrets_engines()['data']
            mount_path_with_slash = f"{self.mount_path}/" if not self.mount_path.endswith('/') else self.mount_path
            
            if mount_path_with_slash not in mounted_engines:
                logger.error(f"KV secrets engine not mounted at {self.mount_path}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Vault: {str(e)}")
            return False
    
    def get_secret(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a secret from Vault.
        
        Args:
            key: Secret key
            
        Returns:
            Optional[Dict[str, Any]]: Secret data or None if not found
        """
        if not self.client:
            if not self.connect():
                return None
        
        try:
            secret = self.client.secrets.kv.v1.read_secret(
                path=key,
                mount_point=self.mount_path
            )
            return secret.get('data')
        except InvalidPath:
            # Secret not found
            return None
        except VaultError as e:
            logger.error(f"Failed to get secret {key}: {str(e)}")
            return None
    
    def set_secret(self, key: str, data: Dict[str, Any]) -> bool:
        """Set a secret in Vault.
        
        Args:
            key: Secret key
            data: Secret data
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.client:
            if not self.connect():
                return False
        
        try:
            self.client.secrets.kv.v1.create_or_update_secret(
                path=key,
                secret=data,
                mount_point=self.mount_path
            )
            return True
        except VaultError as e:
            logger.error(f"Failed to set secret {key}: {str(e)}")
            return False
    
    def delete_secret(self, key: str) -> bool:
        """Delete a secret from Vault.
        
        Args:
            key: Secret key
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.client:
            if not self.connect():
                return False
        
        try:
            self.client.secrets.kv.v1.delete_secret(
                path=key,
                mount_point=self.mount_path
            )
            return True
        except VaultError as e:
            logger.error(f"Failed to delete secret {key}: {str(e)}")
            return False


# Global vault client instance
_vault_client = None


def get_vault_client() -> Optional[VaultClient]:
    """Get the global Vault client instance.
    
    Returns:
        Optional[VaultClient]: Vault client instance or None if not enabled
    """
    global _vault_client
    
    if not ENABLE_VAULT_INTEGRATION:
        return None
    
    if _vault_client is None:
        _vault_client = VaultClient(
            url=VAULT_URL,
            token=VAULT_TOKEN,
            mount_path=VAULT_MOUNT_PATH,
            kv_version=VAULT_VERSION,
            timeout=VAULT_TIMEOUT,
            verify_ssl=VAULT_VERIFY_SSL
        )
    
    return _vault_client


def test_vault_connection(
    url: str,
    token: str,
    mount_path: str = VAULT_MOUNT_PATH,
    kv_version: int = VAULT_VERSION,
    timeout: int = VAULT_TIMEOUT,
    verify_ssl: bool = VAULT_VERIFY_SSL
) -> Tuple[bool, str]:
    """Test connection to Vault server.
    
    Args:
        url: Vault server URL
        token: Vault authentication token
        mount_path: Mount path for the KV secrets engine
        kv_version: KV secrets engine version (1)
        timeout: Request timeout in seconds
        verify_ssl: Whether to verify SSL certificates
        
    Returns:
        Tuple[bool, str]: (success, message)
    """
    try:
        client = VaultClient(
            url=url,
            token=token,
            mount_path=mount_path,
            kv_version=kv_version,
            timeout=timeout,
            verify_ssl=verify_ssl
        )
        
        if client.connect():
            return True, "Successfully connected to Vault"
        else:
            return False, "Failed to connect to Vault"
    except Exception as e:
        return False, f"Error connecting to Vault: {str(e)}"


def format_secret_key(name: str, user_id: str, agent_id: Optional[str] = None, is_common: bool = False) -> str:
    """Format the base Vault secret path: users/<user_id>/<agent_name>.

    Note: The parameter "name" is ignored in the path in the new scheme. The actual
    key (field) is stored inside the secret data at this path, not in the path name.

    Args:
        name: Secret field name (unused for path construction).
        user_id: Vault user id (can be a logical id from header).
        agent_id: Agent identifier (model string); will be sanitized.
        is_common: If True, use "common" scope.

    Returns:
        str: Formatted secret base path (relative to mount point).
    """
    if is_common:
        agent_name = "common"
    elif agent_id:
        agent_name = sanitize_agent_name(agent_id)
    else:
        agent_name = "default"
    return f"users/{user_id}/{agent_name}"


def store_agent_connection_in_vault(connection: Dict[str, Any], user_id: str) -> bool:
    """Store/update an agent connection value in Vault without extra encryption.

    New schema:
      - Path: users/<user_id>/<agent_name>
      - Secret data: { <key_name>: <plain_value>, ... }

    Args:
        connection: Agent connection data containing 'name', 'value', optional 'agent_id', 'is_common'.
        user_id: Vault user id (may come from header).

    Returns:
        bool: True if successful, False otherwise
    """
    if not ENABLE_VAULT_INTEGRATION:
        return False

    client = get_vault_client()
    if not client:
        return False

    name = connection.get("name")
    value = connection.get("value")
    is_common = connection.get("is_common", False)
    agent_id = connection.get("agent_id")

    if not name or value is None:
        return False

    try:
        path = format_secret_key(name, user_id, agent_id, is_common)
        # Merge with existing data to preserve other keys under the same agent secret
        existing = client.get_secret(path) or {}
        # Store using sanitized key field (replace path separators)
        sanitized = sanitize_key_field(name)
        existing[sanitized] = str(value)
        return client.set_secret(path, existing)
    except Exception as e:
        logger.error(f"Failed to store agent connection in vault: {str(e)}")
        return False


def get_agent_connection_from_vault(
    name: str,
    user_id: str,
    is_common: bool = False,
    agent_id: Optional[str] = None
) -> Optional[str]:
    """Get an agent connection value from Vault without extra decryption.

    Args:
        name: Field name within the Vault secret.
        user_id: Vault user id.
        is_common: Whether the secret is common to all agents.
        agent_id: Agent identifier (model string) for agent-specific scope.

    Returns:
        Optional[str]: Secret value or None if not found.
    """
    if not ENABLE_VAULT_INTEGRATION:
        return None

    client = get_vault_client()
    if not client:
        return None

    try:
        # Primary: read from the normalized underscore path
        path = format_secret_key(name, user_id, agent_id, is_common)
        secret = client.get_secret(path)
        if secret:
            sanitized = sanitize_key_field(name)
            if sanitized in secret:
                return secret[sanitized]

        return None
    except Exception as e:
        logger.error(f"Failed to get agent connection from vault: {str(e)}")
        return None


def delete_agent_connection_from_vault(
    name: str,
    user_id: str,
    is_common: bool = False,
    agent_id: Optional[str] = None
) -> bool:
    """Delete an agent connection field from Vault.

    If the secret has no fields left after deletion, remove the secret path.

    Args:
        name: Field name to remove.
        user_id: Vault user id.
        is_common: Whether the secret is common to all agents.
        agent_id: Agent identifier (model string) for agent-specific scope.

    Returns:
        bool: True if successful, False otherwise
    """
    if not ENABLE_VAULT_INTEGRATION:
        return False

    client = get_vault_client()
    if not client:
        return False

    try:
        # Attempt deletion on the normalized underscore path first
        path = format_secret_key(name, user_id, agent_id, is_common)
        secret = client.get_secret(path)
        deleted_any = False
        if secret:
            # Remove sanitized key if present
            sanitized = sanitize_key_field(name)
            if sanitized in secret:
                secret.pop(sanitized, None)
            if secret:
                deleted_any = client.set_secret(path, secret)
            else:
                deleted_any = client.delete_secret(path)

        # If path/field didn't exist, treat as success
        return True if not deleted_any else deleted_any
    except Exception as e:
        logger.error(f"Failed to delete agent connection from vault: {str(e)}")
        return False
