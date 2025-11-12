import pytest
import unittest.mock as mock
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from open_webui.routers.agent_connections import router
from open_webui.utils.vault import (
    store_agent_connection_in_vault,
    get_agent_connection_from_vault,
    delete_agent_connection_from_vault,
    format_secret_key
)


@pytest.fixture
def client():
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestVaultUtils:
    """Test Vault utility functions."""
    
    def test_format_secret_key_common(self):
        """Test format_secret_key for common connections."""
        key = format_secret_key("api_key", "user123", is_common=True)
        assert key == "users/user123/common"
    
    def test_format_secret_key_agent_specific(self):
        """Test format_secret_key for agent-specific connections."""
        key = format_secret_key("api_key", "user123", agent_id="agent456")
        assert key == "users/user123/agent456"
    
    def test_format_secret_key_default(self):
        """Test format_secret_key for default connections."""
        key = format_secret_key("api_key", "user123")
        assert key == "users/user123/default"
    
    @patch('open_webui.utils.vault.ENABLE_VAULT_INTEGRATION', False)
    def test_store_connection_vault_disabled(self):
        """Test storing connection when Vault is disabled."""
        connection = {
            "name": "test_key",
            "value": "test_value",
            "is_common": False,
            "agent_id": "agent123"
        }
        result = store_agent_connection_in_vault(connection, "user123")
        assert result is False
    
    @patch('open_webui.utils.vault.get_vault_client')
    @patch('open_webui.utils.vault.ENABLE_VAULT_INTEGRATION', True)
    def test_store_connection_success(self, mock_get_client):
        """Test successful connection storage."""
        mock_client = MagicMock()
        mock_client.set_secret.return_value = True
        mock_get_client.return_value = mock_client
        
        connection = {
            "name": "test_key",
            "value": "test_value",
            "is_common": False,
            "agent_id": "agent123"
        }
        result = store_agent_connection_in_vault(connection, "user123")
        
        assert result is True
        mock_client.set_secret.assert_called_once()
    
    @patch('open_webui.utils.vault.get_vault_client')
    @patch('open_webui.utils.vault.ENABLE_VAULT_INTEGRATION', True)
    def test_get_connection_success(self, mock_get_client):
        """Test successful connection retrieval."""
        mock_client = MagicMock()
        # New schema stores fields directly under the secret
        mock_client.get_secret.return_value = {"test_key": "test_value"}
        mock_get_client.return_value = mock_client
        
        result = get_agent_connection_from_vault("test_key", "user123", agent_id="agent123")
        
        assert result == "test_value"
        mock_client.get_secret.assert_called_once()
    
    @patch('open_webui.utils.vault.get_vault_client')
    @patch('open_webui.utils.vault.ENABLE_VAULT_INTEGRATION', True)
    def test_delete_connection_success(self, mock_get_client):
        """Test successful connection deletion."""
        mock_client = MagicMock()
        # Provide existing secret with the target field so deletion path is exercised
        mock_client.get_secret.return_value = {"test_key": "test_value"}
        mock_client.delete_secret.return_value = True
        mock_get_client.return_value = mock_client
        
        result = delete_agent_connection_from_vault("test_key", "user123", agent_id="agent123")
        
        assert result is True
        mock_client.delete_secret.assert_called_once()


class TestAgentConnectionsAPI:
    """Test Agent Connections API endpoints."""
    
    @patch('open_webui.routers.agent_connections.get_verified_user')
    @patch('open_webui.routers.agent_connections.store_agent_connection_in_vault')
    @patch('open_webui.routers.agent_connections.VAULT_CONFIG')
    def test_create_connection_success(self, mock_vault_config, mock_store, mock_get_user, client):
        """Test successful connection creation."""
        mock_vault_config.value = True
        mock_store.return_value = True
        mock_user = MagicMock()
        mock_user.id = "user123"
        mock_get_user.return_value = mock_user
        
        connection_data = {
            "key_name": "api_key",
            "key_value": "secret_value",
            "agent_id": "agent123",
            "is_common": False
        }
        
        response = client.post("/", json=connection_data)
        
        assert response.status_code == 200
        body = response.json()
        assert "key_id" in body
        assert body["key_name"] == "api_key"
        assert body["agent_id"] == "agent123"
        assert body["is_common"] is False
    
    @patch('open_webui.routers.agent_connections.get_verified_user')
    def test_create_connection_missing_data(self, mock_get_user, client):
        """Test connection creation with missing data."""
        mock_user = MagicMock()
        mock_user.id = "user123"
        mock_get_user.return_value = mock_user
        
        connection_data = {
            "key_name": "api_key",
            # Missing key_value
            "agent_id": "agent123",
            "is_common": False
        }
        
        response = client.post("/", json=connection_data)
        
        assert response.status_code == 422  # Validation error
    
    @patch('open_webui.routers.agent_connections.get_verified_user')
    @patch('open_webui.routers.agent_connections.get_agent_connection_from_vault')
    @patch('open_webui.routers.agent_connections.VAULT_CONFIG')
    def test_get_connection_success(self, mock_vault_config, mock_get, mock_get_user, client):
        """Test successful connection retrieval."""
        mock_vault_config.value = True
        mock_get.return_value = "secret_value"
        mock_user = MagicMock()
        mock_user.id = "user123"
        mock_user.role = "user"
        mock_get_user.return_value = mock_user
        
        key_id = "user123_api_key_agent123"
        response = client.get(f"/{key_id}")
        
        assert response.status_code == 200
        assert response.json()["key_value"] == "secret_value"
    
    @patch('open_webui.routers.agent_connections.get_verified_user')
    def test_get_connection_access_denied(self, mock_get_user, client):
        """Test connection retrieval with access denied."""
        mock_user = MagicMock()
        mock_user.id = "user456"  # Different user ID
        mock_user.role = "user"
        mock_get_user.return_value = mock_user
        
        key_id = "user123_api_key_agent123"  # Belongs to user123
        response = client.get(f"/{key_id}")
        
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]
    
    @patch('open_webui.routers.agent_connections.get_verified_user')
    @patch('open_webui.routers.agent_connections.delete_agent_connection_from_vault')
    @patch('open_webui.routers.agent_connections.VAULT_CONFIG')
    def test_delete_connection_success(self, mock_vault_config, mock_delete, mock_get_user, client):
        """Test successful connection deletion."""
        mock_vault_config.value = True
        mock_delete.return_value = True
        mock_user = MagicMock()
        mock_user.id = "user123"
        mock_get_user.return_value = mock_user
        
        key_id = "user123_api_key_agent123"
        response = client.delete(f"/{key_id}")
        
        assert response.status_code == 200
        assert response.json()["status"] == "success"


class TestIntegration:
    """Integration tests for the complete flow."""
    
    @patch('open_webui.utils.vault.VaultClient')
    @patch('open_webui.utils.vault.ENABLE_VAULT_INTEGRATION', True)
    def test_full_connection_lifecycle(self, mock_vault_client_class):
        """Test creating, getting, and deleting a connection."""
        mock_client = MagicMock()
        mock_vault_client_class.return_value = mock_client
        mock_client.connect.return_value = True
        
        # Test storage
        connection = {
            "name": "test_key",
            "value": "test_value",
            "is_common": False,
            "agent_id": "agent123"
        }
        
        # Mock successful storage
        mock_client.set_secret.return_value = True
        result = store_agent_connection_in_vault(connection, "user123")
        assert result is True
        
        # Mock successful retrieval (field-based)
        mock_client.get_secret.return_value = {"test_key": "test_value"}
        retrieved_value = get_agent_connection_from_vault(
            "test_key", "user123", agent_id="agent123"
        )
        assert retrieved_value == "test_value"
        
        # Mock successful deletion
        mock_client.get_secret.return_value = {"test_key": "test_value"}
        mock_client.delete_secret.return_value = True
        result = delete_agent_connection_from_vault(
            "test_key", "user123", agent_id="agent123"
        )
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__]) 