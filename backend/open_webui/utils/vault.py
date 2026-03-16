"""
HashiCorp Vault integration for Open WebUI.

This module provides functionality to securely store and retrieve agent connection
secrets in HashiCorp Vault instead of the local database.
"""

import os
import re
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


def sanitize_vault_keys_header(vault_keys_str: str, model: str) -> str:
    """Normalize the x-ltai-vault-keys header value to the format expected by the agent backend.

    The agent backend derives the agent name by sanitizing the model ID:
        agent_name = re.sub(r'[^a-zA-Z0-9]', '_', re.match(r'([^:]+)', model).group(1))

    So for model 'appz/tracker' the expected key format is 'appz_tracker/KEY_NAME'.

    Clients may send the key in the raw format '{model}_{KEY_NAME}' (e.g.
    'appz/tracker_TRACKER_API_KEY'). This function detects both raw and already-sanitized
    formats and normalises them to 'sanitized_model/KEY_NAME'.

    Keys starting with '^' are COMMON-scope and are left untouched.
    """
    if not vault_keys_str or not model:
        return vault_keys_str

    model_base = re.match(r'([^:]+)', model).group(1)  # strip :tag suffix
    sanitized_model = re.sub(r'[^a-zA-Z0-9]', '_', model_base)

    result = []
    for vault_key in vault_keys_str.split(','):
        vault_key = vault_key.strip()
        if not vault_key:
            continue
        if vault_key.startswith('^'):
            result.append(vault_key)
        else:
            # Case 1: raw model prefix with '_' separator – e.g. 'appz/tracker_KEY_NAME'
            raw_prefix = model_base + '_'
            if vault_key.startswith(raw_prefix):
                key_name = vault_key[len(raw_prefix):]
                result.append(f"{sanitized_model}/{key_name}")
            # Case 2: already has '/' separator – sanitize agent-name portion only
            elif '/' in vault_key:
                agent_part, key_part = vault_key.rsplit('/', 1)
                sanitized_agent = re.sub(r'[^a-zA-Z0-9]', '_', agent_part)
                result.append(f"{sanitized_agent}/{key_part}")
            else:
                result.append(vault_key)

    return ','.join(result)


def sanitize_agent_id(agent_id: str) -> str:
    """Sanitize an agent ID for use as a Vault path component.

    Replaces any character that is not alphanumeric with '_', matching the
    same derivation used by the agent backend.
    """
    return re.sub(r'[^a-zA-Z0-9]', '_', agent_id)


def format_secret_path(user_id: str, agent_id: Optional[str] = None, is_common: bool = False) -> str:
    """Return the Vault path for an agent scope.

    Layout (matches agent backend expectation):
        users/<user_id>/COMMON              — common scope
        users/<user_id>/<sanitized_agent>   — agent-specific
        users/<user_id>/default             — no agent

    The secret stored at this path is a dict of { KEY_NAME: plaintext_value }.
    The agent backend reads this path directly and expects plaintext values.
    """
    if is_common:
        return f"users/{user_id}/COMMON"
    elif agent_id:
        return f"users/{user_id}/{sanitize_agent_id(agent_id)}"
    else:
        return f"users/{user_id}/default"


def store_agent_connection_in_vault(connection: Dict[str, Any], user_id: str) -> bool:
    """Store a key in Vault.

    Reads the existing secret at the agent path, merges the new key, and
    writes it back.  Values are stored as plaintext so the agent backend
    can read them directly.

    Path layout: users/<user_id>/<agent_scope>  →  { KEY_NAME: value, ... }
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
        path = format_secret_path(user_id, agent_id, is_common)

        # Read existing keys at this path so we don't overwrite sibling keys
        existing = client.get_secret(path) or {}
        existing[name] = str(value)

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
    """Get a single key value from the agent's Vault secret."""
    if not ENABLE_VAULT_INTEGRATION:
        return None

    client = get_vault_client()
    if not client:
        return None

    try:
        path = format_secret_path(user_id, agent_id, is_common)
        secret = client.get_secret(path)

        if secret and name in secret:
            return secret[name]

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
    """Remove a single key from the agent's Vault secret.

    If the secret becomes empty after removal, the entire path is deleted.
    """
    if not ENABLE_VAULT_INTEGRATION:
        return False

    client = get_vault_client()
    if not client:
        return False

    try:
        path = format_secret_path(user_id, agent_id, is_common)
        existing = client.get_secret(path)

        if not existing or name not in existing:
            return True  # Key doesn't exist — treat as success

        del existing[name]

        if existing:
            return client.set_secret(path, existing)
        else:
            return client.delete_secret(path)
    except Exception as e:
        logger.error(f"Failed to delete agent connection from vault: {str(e)}")
        return False
