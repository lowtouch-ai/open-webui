import pytest
import unittest.mock as mock
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from open_webui.routers.agent_connections import router
from open_webui.utils.vault import (
    store_agent_connection_in_vault,
    get_agent_connection_from_vault,
    delete_agent_connection_from_vault,
    format_secret_path,
    sanitize_agent_id,
    _encrypt_value,
    _decrypt_value
)


@pytest.fixture
def client():
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestSanitizeAgentId:
    """Test agent ID sanitization matches agent backend convention."""

    def test_simple_name(self):
        assert sanitize_agent_id("webshop") == "webshop"

    def test_slash_in_name(self):
        assert sanitize_agent_id("appz/tracker") == "appz_tracker"

    def test_multiple_special_chars(self):
        assert sanitize_agent_id("org/team/model-v2") == "org_team_model_v2"

    def test_with_tag_suffix(self):
        assert sanitize_agent_id("appz/tracker:latest") == "appz_tracker"

    def test_dots_and_dashes(self):
        assert sanitize_agent_id("my.model-name") == "my_model_name"


class TestFormatSecretPath:
    """Test Vault path generation."""

    def test_common_path(self):
        path = format_secret_path("user123", is_common=True)
        assert path == "users/user123/COMMON"

    def test_agent_specific_path(self):
        path = format_secret_path("user123", agent_id="webshop")
        assert path == "users/user123/webshop"

    def test_agent_with_slash_path(self):
        path = format_secret_path("user123", agent_id="appz/tracker")
        assert path == "users/user123/appz_tracker"

    def test_default_path(self):
        path = format_secret_path("user123")
        assert path == "users/user123/default"


class TestVaultUtils:
    """Test Vault utility functions."""

    def test_encrypt_decrypt_value(self):
        """Test encryption and decryption of values."""
        original_value = "test-secret-value"
        encrypted = _encrypt_value(original_value)
        decrypted = _decrypt_value(encrypted)

        assert decrypted == original_value
        assert encrypted != original_value

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
    def test_store_connection_merges_into_existing(self, mock_get_client):
        """Test that storing a key merges it into the existing agent secret."""
        mock_client = MagicMock()
        existing_encrypted = _encrypt_value("old_value")
        mock_client.get_secret.return_value = {"EXISTING_KEY": existing_encrypted}
        mock_client.set_secret.return_value = True
        mock_get_client.return_value = mock_client

        connection = {
            "name": "NEW_KEY",
            "value": "new_value",
            "is_common": False,
            "agent_id": "appz/tracker"
        }
        result = store_agent_connection_in_vault(connection, "user123")

        assert result is True
        # Verify set_secret was called with merged dict at the correct path
        call_args = mock_client.set_secret.call_args
        assert call_args[0][0] == "users/user123/appz_tracker"
        stored_data = call_args[0][1]
        assert "EXISTING_KEY" in stored_data
        assert "NEW_KEY" in stored_data

    @patch('open_webui.utils.vault.get_vault_client')
    @patch('open_webui.utils.vault.ENABLE_VAULT_INTEGRATION', True)
    def test_store_connection_creates_new_secret(self, mock_get_client):
        """Test storing a key when no secret exists yet for the agent."""
        mock_client = MagicMock()
        mock_client.get_secret.return_value = None  # No existing secret
        mock_client.set_secret.return_value = True
        mock_get_client.return_value = mock_client

        connection = {
            "name": "API_KEY",
            "value": "secret123",
            "is_common": False,
            "agent_id": "appz/tracker"
        }
        result = store_agent_connection_in_vault(connection, "user123")

        assert result is True
        call_args = mock_client.set_secret.call_args
        assert call_args[0][0] == "users/user123/appz_tracker"
        stored_data = call_args[0][1]
        assert "API_KEY" in stored_data
        assert len(stored_data) == 1

    @patch('open_webui.utils.vault.get_vault_client')
    @patch('open_webui.utils.vault.ENABLE_VAULT_INTEGRATION', True)
    def test_get_connection_success(self, mock_get_client):
        """Test successful connection retrieval."""
        mock_client = MagicMock()
        encrypted_value = _encrypt_value("test_value")
        mock_client.get_secret.return_value = {"test_key": encrypted_value}
        mock_get_client.return_value = mock_client

        result = get_agent_connection_from_vault("test_key", "user123", agent_id="agent123")

        assert result == "test_value"
        mock_client.get_secret.assert_called_once_with("users/user123/agent123")

    @patch('open_webui.utils.vault.get_vault_client')
    @patch('open_webui.utils.vault.ENABLE_VAULT_INTEGRATION', True)
    def test_get_connection_with_slash_agent(self, mock_get_client):
        """Test retrieval for an agent with slash in its name."""
        mock_client = MagicMock()
        encrypted_value = _encrypt_value("tracker_secret")
        mock_client.get_secret.return_value = {"API_KEY": encrypted_value}
        mock_get_client.return_value = mock_client

        result = get_agent_connection_from_vault("API_KEY", "user123", agent_id="appz/tracker")

        assert result == "tracker_secret"
        mock_client.get_secret.assert_called_once_with("users/user123/appz_tracker")

    @patch('open_webui.utils.vault.get_vault_client')
    @patch('open_webui.utils.vault.ENABLE_VAULT_INTEGRATION', True)
    def test_delete_removes_key_from_dict(self, mock_get_client):
        """Test that deleting a key removes it from the agent secret dict."""
        mock_client = MagicMock()
        enc_val1 = _encrypt_value("val1")
        enc_val2 = _encrypt_value("val2")
        mock_client.get_secret.return_value = {"KEY1": enc_val1, "KEY2": enc_val2}
        mock_client.set_secret.return_value = True
        mock_get_client.return_value = mock_client

        result = delete_agent_connection_from_vault("KEY1", "user123", agent_id="agent123")

        assert result is True
        # Should write back the dict without KEY1
        call_args = mock_client.set_secret.call_args
        stored_data = call_args[0][1]
        assert "KEY1" not in stored_data
        assert "KEY2" in stored_data
        # Should NOT call delete_secret since there are remaining keys
        mock_client.delete_secret.assert_not_called()

    @patch('open_webui.utils.vault.get_vault_client')
    @patch('open_webui.utils.vault.ENABLE_VAULT_INTEGRATION', True)
    def test_delete_last_key_removes_secret(self, mock_get_client):
        """Test that deleting the last key deletes the entire Vault secret."""
        mock_client = MagicMock()
        enc_val = _encrypt_value("val1")
        mock_client.get_secret.return_value = {"ONLY_KEY": enc_val}
        mock_client.delete_secret.return_value = True
        mock_get_client.return_value = mock_client

        result = delete_agent_connection_from_vault("ONLY_KEY", "user123", agent_id="agent123")

        assert result is True
        mock_client.delete_secret.assert_called_once_with("users/user123/agent123")
        mock_client.set_secret.assert_not_called()


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
        mock_user.role = "user"
        mock_get_user.return_value = mock_user

        connection_data = {
            "key_name": "api_key",
            "key_value": "secret_value",
            "agent_id": "appz/tracker",
            "is_common": False
        }

        response = client.post("/", json=connection_data)

        assert response.status_code == 200
        data = response.json()
        assert data["key_name"] == "api_key"
        assert data["agent_id"] == "appz/tracker"
        # key_id should use ':' delimiter with sanitized agent
        assert data["key_id"] == "user123:appz_tracker:api_key"

    @patch('open_webui.routers.agent_connections.get_verified_user')
    def test_create_connection_invalid_name(self, mock_get_user, client):
        """Test connection creation with invalid name."""
        mock_user = MagicMock()
        mock_user.id = "user123"
        mock_get_user.return_value = mock_user

        connection_data = {
            "key_name": "invalid name!",
            "key_value": "secret_value",
            "agent_id": "agent123",
            "is_common": False
        }

        response = client.post("/", json=connection_data)

        assert response.status_code == 400
        assert "alphanumeric" in response.json()["detail"]

    @patch('open_webui.routers.agent_connections.get_verified_user')
    def test_create_connection_missing_data(self, mock_get_user, client):
        """Test connection creation with missing data."""
        mock_user = MagicMock()
        mock_user.id = "user123"
        mock_get_user.return_value = mock_user

        connection_data = {
            "key_name": "api_key",
            "agent_id": "agent123",
            "is_common": False
        }

        response = client.post("/", json=connection_data)

        assert response.status_code == 422

    @patch('open_webui.routers.agent_connections.get_verified_user')
    @patch('open_webui.routers.agent_connections.get_agent_connection_from_vault')
    @patch('open_webui.routers.agent_connections.VAULT_CONFIG')
    def test_get_connection_success(self, mock_vault_config, mock_get, mock_get_user, client):
        """Test successful connection retrieval using new key_id format."""
        mock_vault_config.value = True
        mock_get.return_value = "secret_value"
        mock_user = MagicMock()
        mock_user.id = "user123"
        mock_user.role = "user"
        mock_get_user.return_value = mock_user

        key_id = "user123:appz_tracker:api_key"
        response = client.get(f"/{key_id}")

        assert response.status_code == 200
        assert response.json()["key_value"] == "secret_value"

    @patch('open_webui.routers.agent_connections.get_verified_user')
    def test_get_connection_access_denied(self, mock_get_user, client):
        """Test connection retrieval with access denied."""
        mock_user = MagicMock()
        mock_user.id = "user456"
        mock_user.role = "user"
        mock_get_user.return_value = mock_user

        key_id = "user123:appz_tracker:api_key"
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
        mock_user.role = "user"
        mock_get_user.return_value = mock_user

        key_id = "user123:appz_tracker:api_key"
        response = client.delete(f"/{key_id}")

        assert response.status_code == 200
        assert response.json()["status"] == "success"


class TestIntegration:
    """Integration tests for the complete flow."""

    @patch('open_webui.utils.vault.get_vault_client')
    @patch('open_webui.utils.vault.ENABLE_VAULT_INTEGRATION', True)
    def test_full_connection_lifecycle_with_slash_model(self, mock_get_client):
        """Test creating, getting, and deleting a connection for appz/tracker."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.connect.return_value = True
        mock_client.get_secret.return_value = None  # No existing secret initially
        mock_client.set_secret.return_value = True

        # Store
        connection = {
            "name": "API_KEY",
            "value": "test_value",
            "is_common": False,
            "agent_id": "appz/tracker"
        }
        result = store_agent_connection_in_vault(connection, "user123")
        assert result is True

        # Verify the Vault path is sanitized
        store_call = mock_client.set_secret.call_args
        assert store_call[0][0] == "users/user123/appz_tracker"
        stored_data = store_call[0][1]
        assert "API_KEY" in stored_data

        # Retrieve — mock the stored data
        mock_client.get_secret.return_value = stored_data
        retrieved_value = get_agent_connection_from_vault(
            "API_KEY", "user123", agent_id="appz/tracker"
        )
        assert retrieved_value == "test_value"

        # Delete
        mock_client.delete_secret.return_value = True
        result = delete_agent_connection_from_vault(
            "API_KEY", "user123", agent_id="appz/tracker"
        )
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__])
