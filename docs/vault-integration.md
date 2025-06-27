# HashiCorp Vault Integration for Open WebUI

This document provides comprehensive instructions for setting up and using HashiCorp Vault integration with Open WebUI to securely store agent connection secrets.

## Overview

Open WebUI supports integration with HashiCorp Vault for secure storage and retrieval of agent connection secrets. This integration provides enhanced security compared to storing secrets directly in the application's database or configuration files.

The system uses a modern REST API architecture with AES encryption, user isolation, and comprehensive UI management for agent connections.

## Features

- **Secure Storage**: AES encryption (Fernet) for all secret values before Vault storage
- **User Isolation**: Per-user secret namespacing with path structure `users/<user_id>/<scope>_<key_name>`
- **REST API**: Complete CRUD operations for agent connections
- **Modern UI**: Intuitive interface with search, pagination, and connection management
- **Vault Integration**: Support for KV secrets engine versions 1 and 2
- **Agent Integration**: Automatic header injection for Ollama API calls via `X-LTAI-Vault-Keys`
- **Local Development**: Automated setup scripts for development environments
- **Access Control**: Role-based permissions and secure token management

## Architecture

### Path Structure

Agent connections are stored in Vault using the following path structure:

```
secret/data/users/<user_id>/<scope>_<key_name>
```

Where:
- `<user_id>`: Unique identifier for the user
- `<scope>`: One of:
  - `<agent_id>`: For agent-specific connections
  - `common`: For shared connections across agents
  - `default`: For default/fallback connections
- `<key_name>`: The name of the secret key

Examples:
- `secret/data/users/123/agent-456_api_key`
- `secret/data/users/123/common_shared_token`
- `secret/data/users/123/default_fallback_key`

### Encryption

All secret values are encrypted using **Fernet symmetric encryption** before storage in Vault:

- **Algorithm**: AES 128 in CBC mode with HMAC SHA256
- **Key Derivation**: PBKDF2 with SHA256 (100,000 iterations)
- **Encoding**: Base64 encoding for storage compatibility
- **Salt**: Randomly generated 16-byte salt per encryption
- **Custom Key**: Optional via `VAULT_ENCRYPTION_KEY` environment variable

## Prerequisites

- HashiCorp Vault server (version 1.0.0 or higher)
- Vault KV secrets engine enabled (v1 or v2)
- Vault token with appropriate permissions
- Python cryptography library (automatically installed)

## Configuration

### Environment Variables

Configure Vault integration using these environment variables:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENABLE_VAULT_INTEGRATION` | Enable/disable Vault integration | `false` | Yes |
| `VAULT_URL` | URL of the Vault server | `https://localhost:8200` | Yes |
| `VAULT_TOKEN` | Vault authentication token | `""` | Yes |
| `VAULT_MOUNT_PATH` | Mount path of KV secrets engine | `secret` | No |
| `VAULT_KV_VERSION` | KV secrets engine version (1 or 2) | `2` | No |
| `VAULT_TIMEOUT` | Timeout for Vault operations (seconds) | `30` | No |
| `VAULT_VERIFY_SSL` | Verify SSL certificates | `true` | No |
| `VAULT_ENCRYPTION_KEY` | Custom AES encryption key | `""` | No |

### Docker Compose Example

```yaml
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    environment:
      - ENABLE_VAULT_INTEGRATION=true
      - VAULT_URL=https://vault.example.com:8200
      - VAULT_TOKEN=hvs.your-vault-token
      - VAULT_MOUNT_PATH=secret
      - VAULT_KV_VERSION=2
      - VAULT_TIMEOUT=30
      - VAULT_VERIFY_SSL=true
      - VAULT_ENCRYPTION_KEY=your-custom-encryption-key
    volumes:
      - open-webui:/app/backend/data
    ports:
      - "3000:8080"
```

### UI Configuration

Administrators can configure Vault through the admin interface:

1. **Access Admin Settings**
   - Log in as an administrator
   - Navigate to **Admin Panel** → **Settings**

2. **Configure Vault Settings**
   - Select the **"Vault"** tab
   - Enable Vault integration
   - Enter Vault URL and authentication token
   - Configure mount path and KV version
   - Set timeout and SSL verification options

3. **Test and Save**
   - Click **"Test Connection"** to verify configuration
   - Click **"Save"** to apply changes

## Local Development Setup

Use the automated setup script for local development:

```bash
# Quick setup with Docker (recommended)
./scripts/setup-vault.sh docker

# Binary installation setup
./scripts/setup-vault.sh binary

# Get help and options
./scripts/setup-vault.sh help
```

### What the Setup Script Does

1. **Vault Installation**: Sets up Vault server (Docker or binary)
2. **Configuration**: Creates development-friendly config
3. **Policy Creation**: Establishes proper access policies
4. **Token Generation**: Creates tokens for Open WebUI access
5. **Environment Setup**: Provides configuration variables

### Manual Local Setup

If you prefer manual setup:

```bash
# Start Vault in dev mode
vault server -dev -dev-root-token-id="myroot"

# In another terminal, set environment
export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN="myroot"

# Enable KV v2 engine (if not already enabled)
vault secrets enable -version=2 kv

# Create policy for Open WebUI
vault policy write open-webui-policy - <<EOF
path "secret/data/users/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "secret/metadata/users/*" {
  capabilities = ["list", "read", "delete"]
}
EOF

# Create token for Open WebUI
vault token create -policy=open-webui-policy
```

## REST API Endpoints

Open WebUI provides comprehensive REST API endpoints for managing agent connections:

### Authentication

All API endpoints require authentication via Bearer token:

```http
Authorization: Bearer <your-jwt-token>
```

### Create Agent Connection

Create a new agent connection:

```http
POST /api/v1/agent_connections/
Content-Type: application/json

{
  "key_name": "api_key",
  "key_value": "sk-1234567890abcdef",
  "agent_id": "agent-123",
  "is_common": false
}
```

**Response:**
```json
{
  "key_id": "users/456/agent-123_api_key",
  "key_name": "api_key",
  "key_value": "***masked***",
  "agent_id": "agent-123",
  "is_common": false,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### List Agent Connections

Retrieve all agent connections for the authenticated user:

```http
GET /api/v1/agent_connections/
```

**Response:**
```json
[
  {
    "key_id": "users/456/agent-123_api_key",
    "key_name": "api_key",
    "key_value": "***masked***",
    "agent_id": "agent-123",
    "is_common": false,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

### Get Specific Connection

Retrieve a specific agent connection:

```http
GET /api/v1/agent_connections/{key_id}
```

**Response:**
```json
{
  "key_id": "users/456/agent-123_api_key",
  "key_name": "api_key",
  "key_value": "***masked***",
  "agent_id": "agent-123",
  "is_common": false,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Update Agent Connection

Update an existing agent connection:

```http
PUT /api/v1/agent_connections/{key_id}
Content-Type: application/json

{
  "key_value": "sk-new-secret-value",
  "agent_id": "updated-agent-id"
}
```

**Response:**
```json
{
  "key_id": "users/456/agent-123_api_key",
  "key_name": "api_key",
  "key_value": "***masked***",
  "agent_id": "updated-agent-id",
  "is_common": false,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z"
}
```

### Delete Agent Connection

Delete an agent connection:

```http
DELETE /api/v1/agent_connections/{key_id}
```

**Response:**
```json
{
  "success": true,
  "message": "Agent connection deleted successfully"
}
```

### Error Responses

API endpoints return structured error responses:

```json
{
  "detail": "Agent connection not found"
}
```

Common HTTP status codes:
- `200`: Success
- `201`: Created
- `400`: Bad Request (validation error)
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `500`: Internal Server Error

## User Interface

### Agent Connections Management

The admin interface provides comprehensive connection management:

1. **Connection List**
   - View all agent connections
   - Search and filter connections
   - Pagination for large datasets
   - Masked secret values for security

2. **Add Connection**
   - Modal form for creating new connections
   - Key name and value input
   - Agent ID specification
   - Common connection toggle

3. **Edit Connection**
   - Modify existing connections
   - Update secret values securely
   - Change agent associations

4. **Delete Connection**
   - Confirmation dialog for safety
   - Permanent removal from Vault

### UI Features

- **Search**: Real-time filtering by key name or agent ID
- **Pagination**: Efficient handling of large connection lists
- **Responsive Design**: Works on desktop and mobile devices
- **Security**: All secret values are masked in the interface
- **Validation**: Form validation with helpful error messages
- **Loading States**: Clear feedback during operations

## Integration with Ollama API

Open WebUI automatically integrates agent connections with Ollama API calls through the `X-LTAI-Vault-Keys` header.

### Automatic Header Injection

When making requests to Ollama API, Open WebUI includes relevant connections:

```http
POST /api/chat
Content-Type: application/json
X-LTAI-Vault-Keys: agent-123_api_key,common_shared_token,default_fallback

{
  "model": "llama2",
  "messages": [...]
}
```

### Header Format

The header contains comma-separated key identifiers:
- Format: `<scope>_<key_name>`
- Examples:
  - `agent-123_api_key`: Agent-specific API key
  - `common_shared_token`: Common shared token
  - `default_fallback`: Default fallback key

### Agent Runtime Integration

The agent runtime can parse the header and retrieve secrets:

```python
# Example agent runtime code
vault_keys = request.headers.get('X-LTAI-Vault-Keys', '').split(',')
for key_id in vault_keys:
    if key_id.startswith('agent-123_'):
        # Use this agent's specific keys
        secret_value = vault_client.get_secret(f"users/{user_id}/{key_id}")
```

## Security Best Practices

### Vault Server Security

1. **Use HTTPS**: Always use TLS encryption for Vault communication
2. **Enable Audit Logging**: Track all Vault operations
3. **Implement Backup Strategy**: Regular backups of Vault data
4. **Network Security**: Restrict network access to Vault server
5. **Regular Updates**: Keep Vault server updated

### Token Management

1. **Principle of Least Privilege**: Use tokens with minimal required permissions
2. **Token TTL**: Set appropriate time-to-live for tokens
3. **Token Rotation**: Implement regular token rotation
4. **Avoid Root Tokens**: Never use root tokens in production
5. **Monitor Token Usage**: Track token usage and detect anomalies

### Application Security

1. **Environment Variables**: Store sensitive config in environment variables
2. **Log Sanitization**: Ensure secrets are not logged
3. **Access Control**: Implement proper user authentication and authorization
4. **Input Validation**: Validate all user inputs
5. **Error Handling**: Avoid exposing sensitive information in error messages

### Encryption Best Practices

1. **Custom Encryption Keys**: Use strong, randomly generated encryption keys
2. **Key Rotation**: Implement encryption key rotation procedures
3. **Secure Key Storage**: Store encryption keys securely (separate from Vault token)
4. **Key Backup**: Maintain secure backups of encryption keys

## Monitoring and Troubleshooting

### Health Checks

Monitor Vault integration health:

```bash
# Check Vault server status
vault status

# Test connection from Open WebUI
curl -H "Authorization: Bearer <token>" \
     http://localhost:3000/api/v1/agent_connections/
```

### Common Issues

1. **Connection Refused**
   - Check Vault server is running
   - Verify VAULT_URL is correct
   - Check network connectivity

2. **Permission Denied**
   - Verify token has required permissions
   - Check Vault policies are correctly configured
   - Ensure KV engine is enabled

3. **Encryption Errors**
   - Verify cryptography library is installed
   - Check encryption key format
   - Ensure consistent encryption key usage

4. **Path Not Found**
   - Verify KV engine mount path
   - Check user ID and path structure
   - Ensure secrets exist at expected paths

### Logging

Enable debug logging for troubleshooting:

```bash
# Set log level in environment
export LOG_LEVEL=DEBUG

# Or in docker-compose.yml
environment:
  - LOG_LEVEL=DEBUG
```

### Vault Audit Logs

Enable audit logging in Vault:

```bash
# Enable file audit logging
vault audit enable file file_path=/vault/logs/audit.log

# Enable syslog audit logging
vault audit enable syslog
```

## Migration Guide

### From Legacy Config API

If upgrading from the legacy config-based API:

1. **Backup Existing Data**: Export current agent connections
2. **Update Client Code**: Switch to new REST API endpoints
3. **Test Integration**: Verify all functionality works with new API
4. **Remove Legacy Code**: Clean up old config-based implementations

### From Unencrypted Storage

If migrating from unencrypted secret storage:

1. **Export Secrets**: Extract existing unencrypted secrets
2. **Enable Encryption**: Set up Vault integration with encryption
3. **Re-import Secrets**: Add secrets through new encrypted API
4. **Verify Migration**: Ensure all secrets are accessible
5. **Remove Old Storage**: Clean up unencrypted storage

## Performance Considerations

### Caching

- Vault responses are not cached by default for security
- Consider implementing application-level caching for read-heavy workloads
- Be mindful of cache invalidation for updated secrets

### Connection Pooling

- Vault client uses connection pooling for efficiency
- Configure appropriate timeout values for your environment
- Monitor connection usage and adjust pool sizes if needed

### Batch Operations

- For bulk operations, consider batching requests
- Use transaction boundaries where appropriate
- Monitor Vault server performance under load

## Additional Resources

- [HashiCorp Vault Documentation](https://www.vaultproject.io/docs)
- [Vault KV Secrets Engine](https://www.vaultproject.io/docs/secrets/kv)
- [Vault Token Authentication](https://www.vaultproject.io/docs/auth/token)
- [Vault Security Best Practices](https://learn.hashicorp.com/tutorials/vault/production-hardening)
- [Open WebUI Documentation](https://github.com/open-webui/open-webui)
- [Python Cryptography Library](https://cryptography.io/en/latest/)

## Support

For issues related to:
- **Vault Integration**: Check this documentation and Vault logs
- **API Issues**: Review API endpoint documentation and request/response formats
- **UI Problems**: Check browser console and network requests
- **General Support**: Visit the Open WebUI GitHub repository
