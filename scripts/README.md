# Scripts Directory

This directory contains utility scripts for Open WebUI development and deployment.

## setup-vault.sh

A comprehensive setup script for HashiCorp Vault integration with Open WebUI.

### Usage

```bash
# Setup using Docker (recommended)
./setup-vault.sh docker

# Setup using binary installation
./setup-vault.sh binary

# Show help
./setup-vault.sh help
```

### Features

- **Docker Setup**: Automatically configures Vault using Docker with proper networking and persistence
- **Binary Setup**: Downloads and installs Vault binary for native installation
- **Policy Configuration**: Creates appropriate Vault policies for Open WebUI access
- **Token Generation**: Generates secure tokens with proper permissions
- **KV Engine Setup**: Enables and configures KV v1 secrets engine
- **Development Ready**: Provides all necessary environment variables for local development

### Docker Setup Details

The Docker setup creates:
- Vault server container with persistent storage
- Development-friendly configuration with UI enabled
- Pre-configured policies and tokens
- Network configuration for local access

### Binary Setup Details

The binary setup:
- Auto-detects OS and architecture
- Downloads the latest Vault binary
- Creates configuration files
- Provides step-by-step instructions for initialization

### Requirements

- **Docker Setup**: Docker and Docker Compose
- **Binary Setup**: curl/wget, unzip, and optionally sudo for system installation
- Network access to download Vault binaries/images

### Configuration Output

Both setups provide:
- Vault URL (typically http://localhost:8200)
- Root token for administrative access
- Open WebUI token with restricted permissions
- Environment variables for integration

### Security Notes

- The script creates development-friendly configurations
- For production use, follow HashiCorp's security recommendations
- Replace default tokens with properly managed ones in production
- Enable TLS and proper authentication for production deployments

### Troubleshooting

Common issues and solutions:

1. **Port 8200 already in use**: Stop any existing Vault instances
2. **Docker permission denied**: Ensure user is in docker group
3. **Binary not executable**: Check file permissions after download
4. **Network issues**: Verify internet connectivity for downloads

For more detailed information, see the [Vault Integration Documentation](../docs/vault-integration.md). 