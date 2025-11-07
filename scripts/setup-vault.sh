#!/bin/bash

# Setup script for HashiCorp Vault for Open WebUI
# This script provides options to set up Vault using Docker or binary installation

set -e

VAULT_VERSION="1.18.3"
VAULT_PORT="8200"
VAULT_DATA_DIR="./vault-data"
VAULT_CONFIG_DIR="./vault-config"

print_banner() {
    echo "=========================================="
    echo "  HashiCorp Vault Setup for Open WebUI"
    echo "=========================================="
    echo ""
}

print_usage() {
    echo "Usage: $0 [docker|binary|help]"
    echo ""
    echo "Options:"
    echo "  docker    - Setup Vault using Docker (recommended)"
    echo "  binary    - Setup Vault using binary installation"
    echo "  help      - Show this help message"
    echo ""
}

setup_docker_vault() {
    echo "Setting up Vault using Docker..."
    echo ""
    
    # Create necessary directories
    mkdir -p "$VAULT_DATA_DIR" "$VAULT_CONFIG_DIR"
    
    # Create Vault configuration file
    cat > "$VAULT_CONFIG_DIR/vault.hcl" << 'EOF'
ui = true
disable_mlock = true

storage "file" {
  path = "/vault/data"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = "true"
}

api_addr = "http://127.0.0.1:8200"
cluster_addr = "https://127.0.0.1:8201"
EOF

    # Create docker-compose.yml for Vault
    cat > docker-compose.vault.yml << 'EOF'
version: '3.8'

services:
  vault:
    image: hashicorp/vault:1.18.3
    container_name: open-webui-vault
    cap_add:
      - IPC_LOCK
    environment:
      VAULT_DEV_ROOT_TOKEN_ID: open-webui-root-token
      VAULT_DEV_LISTEN_ADDRESS: 0.0.0.0:8200
    ports:
      - "8200:8200"
    volumes:
      - ./vault-config:/vault/config:ro
      - ./vault-data:/vault/data
    command: vault server -config=/vault/config/vault.hcl
    networks:
      - vault-network

  # Optional: Vault init container for production setup
  vault-init:
    image: hashicorp/vault:1.18.3
    container_name: vault-init
    depends_on:
      - vault
    environment:
      VAULT_ADDR: http://vault:8200
    command: |
      sh -c '
        sleep 10
        if ! vault status >/dev/null 2>&1; then
          echo "Initializing Vault..."
          vault operator init -key-shares=1 -key-threshold=1 -format=json > /vault/data/init-keys.json
          echo "Vault initialized. Keys saved to /vault/data/init-keys.json"
        else
          echo "Vault already initialized"
        fi
      '
    volumes:
      - ./vault-data:/vault/data
    networks:
      - vault-network
    profiles:
      - init

networks:
  vault-network:
    driver: bridge
EOF

    echo "✓ Created Vault configuration and Docker Compose file"
    echo ""
    echo "Starting Vault container..."
    docker-compose -f docker-compose.vault.yml up -d vault
    
    echo ""
    echo "Waiting for Vault to start..."
    sleep 10
    
    # Check if Vault is running
    if ! curl -s http://localhost:8200/v1/sys/health >/dev/null; then
        echo "❌ Vault failed to start. Check logs with: docker logs open-webui-vault"
        exit 1
    fi
    
    echo "✓ Vault is running!"
    echo ""
    echo "🔧 Configuring Vault for Open WebUI..."
    
    # Set Vault address
    export VAULT_ADDR=http://localhost:8200
    
    # For development mode, we use a simple root token
    export VAULT_TOKEN=open-webui-root-token
    
    # Enable KV secrets engine at 'secret' path
    if ! vault secrets list | grep -q "secret/"; then
        vault secrets enable -path=secret kv-v2
        echo "✓ Enabled KV v2 secrets engine at 'secret/' path"
    else
        echo "✓ KV secrets engine already enabled"
    fi
    
    # Create a policy for Open WebUI
    vault policy write open-webui-policy - << 'EOF'
# Allow managing secrets under secret/data/users/*
path "secret/data/users/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/users/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# Allow listing users directory
path "secret/metadata/users" {
  capabilities = ["list"]
}
EOF
    
    echo "✓ Created Open WebUI policy"
    
    # Create a token for Open WebUI
    OPENWEBUI_TOKEN=$(vault write -field=token auth/token/create \
        policies="open-webui-policy" \
        renewable=true \
        ttl=8760h)
    
    echo "✓ Created token for Open WebUI"
    echo ""
    echo "📝 Configuration Summary:"
    echo "========================"
    echo "Vault URL: http://localhost:8200"
    echo "Root Token: open-webui-root-token"
    echo "Open WebUI Token: $OPENWEBUI_TOKEN"
    echo "KV Mount Path: secret"
    echo "KV Version: 2"
    echo ""
    echo "🔗 Environment Variables for Open WebUI:"
    echo "========================================"
    echo "export ENABLE_VAULT_INTEGRATION=true"
    echo "export VAULT_URL=http://localhost:8200"
    echo "export VAULT_TOKEN=$OPENWEBUI_TOKEN"
    echo "export VAULT_MOUNT_PATH=secret"
    echo "export VAULT_VERSION=2"
    echo ""
    echo "🌐 Vault UI: http://localhost:8200/ui"
    echo ""
}

setup_binary_vault() {
    echo "Setting up Vault using binary installation..."
    echo ""
    
    # Detect OS and architecture
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m)
    
    case $ARCH in
        x86_64) ARCH="amd64" ;;
        aarch64|arm64) ARCH="arm64" ;;
        armv7l) ARCH="arm" ;;
        *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
    esac
    
    VAULT_ZIP="vault_${VAULT_VERSION}_${OS}_${ARCH}.zip"
    VAULT_URL="https://releases.hashicorp.com/vault/${VAULT_VERSION}/${VAULT_ZIP}"
    
    echo "Downloading Vault ${VAULT_VERSION} for ${OS}/${ARCH}..."
    
    # Download Vault binary
    if command -v wget >/dev/null; then
        wget -q "$VAULT_URL" -O "$VAULT_ZIP"
    elif command -v curl >/dev/null; then
        curl -sL "$VAULT_URL" -o "$VAULT_ZIP"
    else
        echo "❌ Neither wget nor curl found. Please install one of them."
        exit 1
    fi
    
    # Extract and install
    unzip -q "$VAULT_ZIP"
    chmod +x vault
    
    # Move to /usr/local/bin if we have permission, otherwise keep in current directory
    if sudo -n true 2>/dev/null; then
        sudo mv vault /usr/local/bin/
        VAULT_BIN="/usr/local/bin/vault"
    else
        echo "⚠️  No sudo access. Vault binary will remain in current directory."
        VAULT_BIN="./vault"
    fi
    
    # Cleanup
    rm "$VAULT_ZIP"
    
    echo "✓ Vault binary installed"
    
    # Create directories
    mkdir -p "$VAULT_DATA_DIR" "$VAULT_CONFIG_DIR"
    
    # Create configuration
    cat > "$VAULT_CONFIG_DIR/vault.hcl" << 'EOF'
ui = true
disable_mlock = true

storage "file" {
  path = "./vault-data"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = "true"
}

api_addr = "http://127.0.0.1:8200"
cluster_addr = "https://127.0.0.1:8201"
EOF

    echo "✓ Created Vault configuration"
    echo ""
    echo "🚀 Starting Vault server..."
    echo ""
    echo "Run the following commands to start and configure Vault:"
    echo ""
    echo "1. Start Vault server (in a separate terminal):"
    echo "   $VAULT_BIN server -config=$VAULT_CONFIG_DIR/vault.hcl"
    echo ""
    echo "2. In another terminal, set environment and initialize:"
    echo "   export VAULT_ADDR=http://localhost:8200"
    echo "   $VAULT_BIN operator init -key-shares=1 -key-threshold=1"
    echo ""
    echo "3. Unseal Vault with the key from step 2:"
    echo "   $VAULT_BIN operator unseal <unseal_key>"
    echo ""
    echo "4. Login with root token from step 2:"
    echo "   $VAULT_BIN auth <root_token>"
    echo ""
    echo "5. Enable KV secrets engine:"
    echo "   $VAULT_BIN secrets enable -path=secret kv-v2"
    echo ""
    echo "6. Create policy and token for Open WebUI:"
    echo "   $VAULT_BIN policy write open-webui-policy - << 'EOF'"
    echo "path \"secret/data/users/*\" {"
    echo "  capabilities = [\"create\", \"read\", \"update\", \"delete\", \"list\"]"
    echo "}"
    echo "path \"secret/metadata/users/*\" {"
    echo "  capabilities = [\"create\", \"read\", \"update\", \"delete\", \"list\"]"
    echo "}"
    echo "path \"secret/metadata/users\" {"
    echo "  capabilities = [\"list\"]"
    echo "}"
    echo "EOF"
    echo ""
    echo "   $VAULT_BIN write auth/token/create policies=\"open-webui-policy\" renewable=true ttl=8760h"
    echo ""
}

# Main script
print_banner

case "${1:-help}" in
    docker)
        setup_docker_vault
        ;;
    binary)
        setup_binary_vault
        ;;
    help|*)
        print_usage
        ;;
esac

echo "🎉 Vault setup complete!"
echo ""
echo "For more information, visit:"
echo "- Vault Documentation: https://developer.hashicorp.com/vault/docs"
echo "- Open WebUI Vault Integration: https://github.com/open-webui/open-webui/blob/main/docs/vault-integration.md" 