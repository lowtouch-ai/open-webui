# HashiCorp Vault Integration for Open WebUI

This document provides instructions for setting up and using HashiCorp Vault integration with Open WebUI to securely store agent connection secrets.

## Overview

Open WebUI supports integration with HashiCorp Vault for secure storage and retrieval of agent connection secrets. This integration provides enhanced security compared to storing secrets directly in the application's database or configuration files.

## Features

- Support for Vault KV secrets engine versions 1 and 2
- Configuration via environment variables or UI
- Connection testing functionality
- Secure storage and retrieval of agent connection secrets
- Role-based access control for Vault tokens

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

- For common connections: `agent_connections/common/{connection_name}`
- For agent-specific connections: `agent_connections/agent/{agent_id}/{connection_name}`

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
