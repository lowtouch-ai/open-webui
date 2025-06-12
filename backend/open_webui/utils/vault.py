"""
HashiCorp Vault integration for Open WebUI.

This module provides functionality to securely store and retrieve agent connection
secrets in HashiCorp Vault instead of the local database.
"""

import os
import logging
from typing import Dict, Any, Optional, List, Tuple

import hvac
from hvac.exceptions import VaultError, InvalidPath

logger = logging.getLogger(__name__)

# Environment variable configuration
VAULT_URL = os.environ.get("VAULT_URL", "http://localhost:8200")
VAULT_TOKEN = os.environ.get("VAULT_TOKEN", "")
VAULT_MOUNT_PATH = os.environ.get("VAULT_MOUNT_PATH", "secret")
VAULT_VERSION = int(os.environ.get("VAULT_VERSION", "2"))
ENABLE_VAULT_INTEGRATION = os.environ.get("ENABLE_VAULT_INTEGRATION", "false").lower() == "true"
VAULT_TIMEOUT = int(os.environ.get("VAULT_TIMEOUT", "30"))
VAULT_VERIFY_SSL = os.environ.get("VAULT_VERIFY_SSL", "true").lower() == "true"


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
            kv_version: KV secrets engine version (1 or 2)
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
        if self.kv_version not in [1, 2]:
            raise ValueError("KV version must be 1 or 2")
    
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
            if self.mount_path not in self.client.sys.list_mounted_secrets_engines()['data']:
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
            if self.kv_version == 1:
                secret = self.client.secrets.kv.v1.read_secret(
                    path=key,
                    mount_point=self.mount_path
                )
                return secret.get('data')
            else:  # KV v2
                secret = self.client.secrets.kv.v2.read_secret_version(
                    path=key,
                    mount_point=self.mount_path
                )
                return secret.get('data', {}).get('data')
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
            if self.kv_version == 1:
                self.client.secrets.kv.v1.create_or_update_secret(
                    path=key,
                    secret=data,
                    mount_point=self.mount_path
                )
            else:  # KV v2
                self.client.secrets.kv.v2.create_or_update_secret(
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
            if self.kv_version == 1:
                self.client.secrets.kv.v1.delete_secret(
                    path=key,
                    mount_point=self.mount_path
                )
            else:  # KV v2
                self.client.secrets.kv.v2.delete_latest_version_of_secret(
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
        kv_version: KV secrets engine version (1 or 2)
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


def format_secret_key(name: str, is_common: bool = False, agent_id: Optional[str] = None) -> str:
    """Format a secret key for Vault.
    
    Args:
        name: Secret name
        is_common: Whether the secret is common to all agents
        agent_id: Agent ID if not common
        
    Returns:
        str: Formatted secret key
    """
    if is_common:
        return f"COMMON_{name}"
    elif agent_id:
        return f"{agent_id}_{name}"
    else:
        return name


def store_agent_connection_in_vault(connection: Dict[str, Any]) -> bool:
    """Store an agent connection in Vault.
    
    Args:
        connection: Agent connection data
        
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
    
    key = format_secret_key(name, is_common, agent_id)
    data = {"value": value}
    
    return client.set_secret(key, data)


def get_agent_connection_from_vault(
    name: str,
    is_common: bool = False,
    agent_id: Optional[str] = None
) -> Optional[str]:
    """Get an agent connection from Vault.
    
    Args:
        name: Secret name
        is_common: Whether the secret is common to all agents
        agent_id: Agent ID if not common
        
    Returns:
        Optional[str]: Secret value or None if not found
    """
    if not ENABLE_VAULT_INTEGRATION:
        return None
    
    client = get_vault_client()
    if not client:
        return None
    
    key = format_secret_key(name, is_common, agent_id)
    secret = client.get_secret(key)
    
    if secret and "value" in secret:
        return secret["value"]
    
    return None


def delete_agent_connection_from_vault(
    name: str,
    is_common: bool = False,
    agent_id: Optional[str] = None
) -> bool:
    """Delete an agent connection from Vault.
    
    Args:
        name: Secret name
        is_common: Whether the secret is common to all agents
        agent_id: Agent ID if not common
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not ENABLE_VAULT_INTEGRATION:
        return False
    
    client = get_vault_client()
    if not client:
        return False
    
    key = format_secret_key(name, is_common, agent_id)
    return client.delete_secret(key)
