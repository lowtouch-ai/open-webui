"""
HashiCorp Vault integration for Open WebUI.

This module provides functionality to securely store and retrieve agent connection
secrets in HashiCorp Vault instead of the local database.
"""

import os
import base64
from typing import Dict, Any, Optional, List, Tuple

import hvac
from hvac.exceptions import VaultError, InvalidPath
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from loguru import logger

# Environment variable configuration
VAULT_URL = os.environ.get("VAULT_URL", "http://localhost:8200")
VAULT_TOKEN = os.environ.get("VAULT_TOKEN", "")
VAULT_MOUNT_PATH = os.environ.get("VAULT_MOUNT_PATH", "secret")
VAULT_VERSION = int(os.environ.get("VAULT_VERSION", "1"))
ENABLE_VAULT_INTEGRATION = os.environ.get("ENABLE_VAULT_INTEGRATION", "false").lower() == "true"
VAULT_TIMEOUT = int(os.environ.get("VAULT_TIMEOUT", "30"))
VAULT_VERIFY_SSL = os.environ.get("VAULT_VERIFY_SSL", "true").lower() == "true"
VAULT_ENCRYPTION_KEY = os.environ.get("VAULT_ENCRYPTION_KEY", "")


def _get_encryption_key() -> bytes:
    """Get or generate encryption key for AES encryption.
    
    Returns:
        bytes: Encryption key
    """
    if VAULT_ENCRYPTION_KEY:
        # Use provided key
        key = VAULT_ENCRYPTION_KEY.encode()
    else:
        # Generate a key from a default password (in production, this should be configurable)
        password = b"open-webui-vault-encryption-key"
        salt = b"open-webui-salt"  # In production, this should be random and stored securely
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
    
    return key


def _encrypt_value(value: str) -> str:
    """Encrypt a value using AES.
    
    Args:
        value: Value to encrypt
        
    Returns:
        str: Base64 encoded encrypted value
    """
    try:
        fernet = Fernet(_get_encryption_key())
        encrypted_value = fernet.encrypt(value.encode())
        return base64.b64encode(encrypted_value).decode()
    except Exception as e:
        logger.error(f"Failed to encrypt value: {str(e)}")
        raise


def _decrypt_value(encrypted_value: str) -> str:
    """Decrypt a value using AES.
    
    Args:
        encrypted_value: Base64 encoded encrypted value
        
    Returns:
        str: Decrypted value
    """
    try:
        fernet = Fernet(_get_encryption_key())
        encrypted_bytes = base64.b64decode(encrypted_value.encode())
        decrypted_value = fernet.decrypt(encrypted_bytes)
        return decrypted_value.decode()
    except Exception as e:
        logger.error(f"Failed to decrypt value: {str(e)}")
        raise


def sanitize_agent_id(agent_id: Optional[str]) -> Optional[str]:
    """Sanitize agent identifier for safe Vault key usage.
    
    Replaces forward slashes with underscores to avoid unintended subpaths
    in Vault when constructing keys.
    
    Args:
        agent_id: Raw agent identifier (may be None)
    
    Returns:
        Optional[str]: Sanitized agent identifier or None
    """
    if agent_id is None:
        return None
    try:
        return agent_id.replace('/', '_')
    except Exception:
        # In the unlikely event of a non-string type sneaking in
        return str(agent_id).replace('/', '_')


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
    """Format a secret key for Vault using the path structure: users/<user_id>/<agent_name>_<key_name>
    
    Args:
        name: Secret name (key_name)
        user_id: User ID
        agent_id: Agent ID (agent_name), optional
        is_common: Whether the secret is common to all agents
        
    Returns:
        str: Formatted secret key path
    """
    if is_common:
        # For common connections, use 'common' as the agent name
        return f"users/{user_id}/common_{name}"
    elif agent_id:
        safe_agent_id = sanitize_agent_id(agent_id)
        return f"users/{user_id}/{safe_agent_id}_{name}"
    else:
        # If no agent_id specified, use 'default' as the agent name
        return f"users/{user_id}/default_{name}"


def store_agent_connection_in_vault(connection: Dict[str, Any], user_id: str) -> bool:
    """Store an agent connection in Vault with AES encryption.
    
    Args:
        connection: Agent connection data
        user_id: User ID for the path structure
        
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
        # Encrypt the value before storing
        encrypted_value = _encrypt_value(str(value))
        
        key = format_secret_key(name, user_id, agent_id, is_common)
        data = {"value": encrypted_value}
        
        return client.set_secret(key, data)
    except Exception as e:
        logger.error(f"Failed to store agent connection in vault: {str(e)}")
        return False


def get_agent_connection_from_vault(
    name: str,
    user_id: str,
    is_common: bool = False,
    agent_id: Optional[str] = None
) -> Optional[str]:
    """Get an agent connection from Vault and decrypt it.
    
    Args:
        name: Secret name
        user_id: User ID for the path structure
        is_common: Whether the secret is common to all agents
        agent_id: Agent ID if not common
        
    Returns:
        Optional[str]: Decrypted secret value or None if not found
    """
    if not ENABLE_VAULT_INTEGRATION:
        return None
    
    client = get_vault_client()
    if not client:
        return None
    
    try:
        key = format_secret_key(name, user_id, agent_id, is_common)
        secret = client.get_secret(key)
        
        if secret and "value" in secret:
            # Decrypt the value before returning
            return _decrypt_value(secret["value"])
        
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
    """Delete an agent connection from Vault.
    
    Args:
        name: Secret name
        user_id: User ID for the path structure
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
    
    try:
        key = format_secret_key(name, user_id, agent_id, is_common)
        return client.delete_secret(key)
    except Exception as e:
        logger.error(f"Failed to delete agent connection from vault: {str(e)}")
        return False
