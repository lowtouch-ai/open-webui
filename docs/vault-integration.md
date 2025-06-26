# HashiCorp Vault Integration for Open WebUI

This document provides instructions for setting up and using HashiCorp Vault integration with Open WebUI to securely store agent connection secrets.

## Overview

Open WebUI supports integration with HashiCorp Vault for secure storage and retrieval of agent connection secrets. This integration provides enhanced security compared to storing secrets directly in the application's database or configuration files.

## Features

- Support for Vault KV secrets engine versions 1 and 2
- Configuration via environment variables or UI
- Connection testing functionality
- Secure storage and retrieval of agent connection secrets with AES encryption
- Role-based access control for Vault tokens
- REST API endpoints for managing agent connections
- Integration with Ollama API via X-LTAI-Vault-Keys header
- Local Vault setup support for development

## Prerequisites

- A running HashiCorp Vault server (version 1.0.0 or higher)
- Vault KV secrets engine enabled (v1 or v2)
- A Vault token with appropriate permissions

## Configuration

### Environment Variables

You can configure the Vault integration using the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `ENABLE_VAULT_INTEGRATION` | Enable or disable Vault integration | `false` |
| `VAULT_URL` | URL of the Vault server | `https://localhost:8200` |
| `VAULT_TOKEN` | Vault authentication token | `""` |
| `VAULT_MOUNT_PATH` | Mount path of the KV secrets engine | `secret` |
| `VAULT_KV_VERSION` | Version of the KV secrets engine (1 or 2) | `2` |
| `VAULT_TIMEOUT` | Timeout for Vault operations in seconds | `30` |
| `VAULT_VERIFY_SSL` | Whether to verify SSL certificates | `true` |
| `VAULT_ENCRYPTION_KEY` | Custom encryption key for AES encryption (optional) | `""` |

Example in docker-compose.yaml:

```yaml
services:
  open-webui:
    environment:
      - ENABLE_VAULT_INTEGRATION=true
      - VAULT_URL=https://vault.example.com:8200
      - VAULT_TOKEN=hvs.your-vault-token
      - VAULT_MOUNT_PATH=secret
      - VAULT_KV_VERSION=2
      - VAULT_TIMEOUT=30
      - VAULT_VERIFY_SSL=true
```

### UI Configuration

Administrators can configure Vault integration through the admin settings UI:

1. Log in as an administrator
2. Navigate to Admin Settings
3. Select the "Vault" tab
4. Configure the Vault settings:
   - Enable/disable Vault integration
   - Set Vault URL
   - Provide Vault token
   - Configure mount path and KV version
   - Set timeout and SSL verification options
5. Click "Test Connection" to verify the configuration
6. Click "Save" to apply the changes

## Local Development Setup

For local development, you can set up Vault using the provided setup script:

```bash
# Using Docker (recommended)
./scripts/setup-vault.sh docker

# Using binary installation
./scripts/setup-vault.sh binary
```

The script will:
- Set up Vault with the correct configuration
- Enable KV v2 secrets engine
- Create appropriate policies for Open WebUI
- Generate tokens for secure access
- Provide environment variables for configuration

## API Endpoints

Open WebUI provides REST API endpoints for managing agent connections:

### Create Connection
```http
POST /api/v1/agent_connections/
Content-Type: application/json

{
  "key_name": "api_key",
  "key_value": "secret-value",
  "agent_id": "agent-123",
  "is_common": false
}
```

### List Connections
```http
GET /api/v1/agent_connections/
```

### Get Connection
```http
GET /api/v1/agent_connections/{key_id}
```

### Update Connection
```http
PUT /api/v1/agent_connections/{key_id}
Content-Type: application/json

{
  "key_value": "new-secret-value"
}
```

### Delete Connection
```http
DELETE /api/v1/agent_connections/{key_id}
```

## Integration with Ollama API

When making requests to Ollama API (for OpenWebUI-Agentomatic communication), Open WebUI automatically includes relevant agent connections in the `X-LTAI-Vault-Keys` header:

```http
X-LTAI-Vault-Keys: agent1_api_key,COMMON_shared_key,agent2_token
```

This allows the agent runtime to retrieve and use the appropriate secrets for API calls.

## Security Best Practices

### Vault Token

- Use a role-based token with the minimum required permissions
- Avoid using the root token in production
- Set an appropriate TTL for the token
- Implement token rotation policies

### Vault Server

- Use HTTPS for Vault server communication
- Enable audit logging in Vault
- Implement proper backup strategies for Vault data
- Follow HashiCorp's security recommendations for Vault deployment

### Secret Naming Conventions

Agent connection secrets in Vault follow this naming convention:

- Path structure: `secret/data/users/<user_id>/<agent_name>_<key_name>`
- For common connections: `secret/data/users/<user_id>/common_<key_name>`
- For agent-specific connections: `secret/data/users/<user_id>/<agent_id>_<key_name>`
- For default connections: `secret/data/users/<user_id>/default_<key_name>`

### Encryption

All secret values are encrypted using AES encryption before being stored in Vault:

- Uses Fernet symmetric encryption (AES 128 in CBC mode with HMAC SHA256)
- Encryption key can be provided via `VAULT_ENCRYPTION_KEY` environment variable
- If no custom key is provided, a default key is derived using PBKDF2

## Troubleshooting

### Connection Issues

- Verify that the Vault server is running and accessible
- Check that the Vault URL is correct and includes the protocol (http/https)
- Ensure the Vault token has appropriate permissions
- Verify SSL certificate if using HTTPS with SSL verification enabled

### Permission Issues

- Ensure the Vault token has read/write permissions for the KV secrets engine
- Check that the KV secrets engine is enabled at the specified mount path
- Verify that the KV version setting matches the actual version in Vault

## Additional Resources

- [HashiCorp Vault Documentation](https://www.vaultproject.io/docs)
- [Vault KV Secrets Engine](https://www.vaultproject.io/docs/secrets/kv)
- [Vault Token Authentication](https://www.vaultproject.io/docs/auth/token)
- [Open WebUI Documentation](https://github.com/open-webui/open-webui)
