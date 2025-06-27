# Agent Connections API Documentation

This document provides detailed information about the Agent Connections REST API endpoints in Open WebUI.

## Overview

The Agent Connections API allows secure management of API keys and secrets for agents through HashiCorp Vault integration. All secret values are encrypted using AES encryption before storage and are user-isolated for security.

## Base URL

```
/api/v1/agent_connections
```

## Authentication

All API endpoints require authentication using a Bearer token in the Authorization header:

```http
Authorization: Bearer <jwt-token>
```

## Data Models

### AgentConnection

Represents an agent connection with encrypted secret storage.

```typescript
interface AgentConnection {
  key_id: string;          // Unique identifier (path in Vault)
  key_name: string;        // Name of the secret key
  key_value: string;       // Secret value (masked in responses)
  agent_id?: string;       // Agent identifier (optional)
  is_common: boolean;      // Whether connection is shared across agents
  created_at: string;      // ISO timestamp of creation
  updated_at: string;      // ISO timestamp of last update
}
```

### AgentConnectionCreate

Data required to create a new agent connection.

```typescript
interface AgentConnectionCreate {
  key_name: string;        // Name of the secret key
  key_value: string;       // Secret value to encrypt and store
  agent_id?: string;       // Agent identifier (optional)
  is_common: boolean;      // Whether connection is shared across agents
}
```

### AgentConnectionUpdate

Data that can be updated in an existing agent connection.

```typescript
interface AgentConnectionUpdate {
  key_value?: string;      // New secret value (optional)
  agent_id?: string;       // New agent identifier (optional)
}
```

## API Endpoints

### Create Agent Connection

Creates a new agent connection with encrypted secret storage.

**Endpoint:** `POST /api/v1/agent_connections/`

**Request Body:**
```json
{
  "key_name": "api_key",
  "key_value": "sk-1234567890abcdef",
  "agent_id": "agent-123",
  "is_common": false
}
```

**Response:** `201 Created`
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

**Validation Rules:**
- `key_name`: Required, 1-100 characters, alphanumeric and underscores only
- `key_value`: Required, 1-1000 characters
- `agent_id`: Optional, 1-100 characters if provided
- `is_common`: Required boolean

**Error Responses:**
- `400 Bad Request`: Invalid input data
- `401 Unauthorized`: Missing or invalid authentication
- `409 Conflict`: Connection with same key_name and scope already exists
- `500 Internal Server Error`: Vault or encryption error

### List Agent Connections

Retrieves all agent connections for the authenticated user.

**Endpoint:** `GET /api/v1/agent_connections/`

**Response:** `200 OK`
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
  },
  {
    "key_id": "users/456/common_shared_token",
    "key_name": "shared_token",
    "key_value": "***masked***",
    "agent_id": null,
    "is_common": true,
    "created_at": "2024-01-15T09:15:00Z",
    "updated_at": "2024-01-15T09:15:00Z"
  }
]
```

**Error Responses:**
- `401 Unauthorized`: Missing or invalid authentication
- `500 Internal Server Error`: Vault error

### Get Specific Agent Connection

Retrieves a specific agent connection by key_id.

**Endpoint:** `GET /api/v1/agent_connections/{key_id}`

**Path Parameters:**
- `key_id`: The unique identifier of the connection (URL encoded)

**Response:** `200 OK`
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

**Error Responses:**
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Connection belongs to different user
- `404 Not Found`: Connection does not exist
- `500 Internal Server Error`: Vault error

### Update Agent Connection

Updates an existing agent connection. Only provided fields are updated.

**Endpoint:** `PUT /api/v1/agent_connections/{key_id}`

**Path Parameters:**
- `key_id`: The unique identifier of the connection (URL encoded)

**Request Body:**
```json
{
  "key_value": "sk-new-secret-value",
  "agent_id": "updated-agent-id"
}
```

**Response:** `200 OK`
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

**Validation Rules:**
- `key_value`: Optional, 1-1000 characters if provided
- `agent_id`: Optional, 1-100 characters if provided

**Error Responses:**
- `400 Bad Request`: Invalid input data
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Connection belongs to different user
- `404 Not Found`: Connection does not exist
- `500 Internal Server Error`: Vault or encryption error

### Delete Agent Connection

Permanently deletes an agent connection from Vault.

**Endpoint:** `DELETE /api/v1/agent_connections/{key_id}`

**Path Parameters:**
- `key_id`: The unique identifier of the connection (URL encoded)

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Agent connection deleted successfully"
}
```

**Error Responses:**
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Connection belongs to different user
- `404 Not Found`: Connection does not exist
- `500 Internal Server Error`: Vault error

## Key ID Format

The `key_id` follows a specific format based on the connection scope:

- **Agent-specific**: `users/{user_id}/{agent_id}_{key_name}`
- **Common**: `users/{user_id}/common_{key_name}`
- **Default**: `users/{user_id}/default_{key_name}`

Examples:
- `users/123/agent-456_api_key`
- `users/123/common_shared_token`
- `users/123/default_fallback_key`

## Security Features

### Value Masking

All API responses mask secret values with `***masked***` for security. The actual encrypted values are never returned in API responses.

### User Isolation

Each user's connections are isolated using their user ID in the Vault path. Users cannot access connections belonging to other users.

### Encryption

All secret values are encrypted using Fernet (AES 128 CBC + HMAC SHA256) before storage in Vault:

- Key derivation using PBKDF2 with 100,000 iterations
- Random salt generation for each encryption
- Base64 encoding for storage compatibility

### Access Control

- JWT token authentication required for all endpoints
- User-specific access control based on token claims
- Vault policies restrict access to user-specific paths

## Error Handling

### Standard Error Format

All error responses follow a consistent format:

```json
{
  "detail": "Error description"
}
```

### HTTP Status Codes

- `200 OK`: Successful operation
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data or validation error
- `401 Unauthorized`: Missing or invalid authentication token
- `403 Forbidden`: Access denied (user doesn't own resource)
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource already exists
- `500 Internal Server Error`: Server error (Vault, encryption, etc.)

### Common Error Messages

- `"Invalid key_name format"`: Key name contains invalid characters
- `"Key value too long"`: Secret value exceeds maximum length
- `"Agent connection not found"`: Connection doesn't exist or access denied
- `"Connection already exists"`: Duplicate key_name for same scope
- `"Vault operation failed"`: Error communicating with Vault
- `"Encryption failed"`: Error encrypting secret value

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **Per User**: 100 requests per minute
- **Per IP**: 1000 requests per minute
- **Burst**: Up to 10 requests in 1 second

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Request limit per window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Timestamp when window resets

## Usage Examples

### cURL Examples

**Create a connection:**
```bash
curl -X POST "http://localhost:3000/api/v1/agent_connections/" \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "key_name": "openai_api_key",
    "key_value": "sk-1234567890abcdef",
    "agent_id": "gpt-agent",
    "is_common": false
  }'
```

**List connections:**
```bash
curl -X GET "http://localhost:3000/api/v1/agent_connections/" \
  -H "Authorization: Bearer your-jwt-token"
```

**Update a connection:**
```bash
curl -X PUT "http://localhost:3000/api/v1/agent_connections/users%2F123%2Fgpt-agent_openai_api_key" \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "key_value": "sk-new-secret-key"
  }'
```

**Delete a connection:**
```bash
curl -X DELETE "http://localhost:3000/api/v1/agent_connections/users%2F123%2Fgpt-agent_openai_api_key" \
  -H "Authorization: Bearer your-jwt-token"
```

### JavaScript Examples

**Using fetch API:**
```javascript
// Create connection
const createConnection = async (token, connectionData) => {
  const response = await fetch('/api/v1/agent_connections/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(connectionData)
  });
  return response.json();
};

// List connections
const listConnections = async (token) => {
  const response = await fetch('/api/v1/agent_connections/', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
};

// Update connection
const updateConnection = async (token, keyId, updateData) => {
  const response = await fetch(`/api/v1/agent_connections/${encodeURIComponent(keyId)}`, {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(updateData)
  });
  return response.json();
};
```

## Integration with Ollama API

When making requests to Ollama API, Open WebUI automatically includes relevant agent connections in the `X-LTAI-Vault-Keys` header:

```http
X-LTAI-Vault-Keys: gpt-agent_openai_api_key,common_shared_token,default_fallback
```

The agent runtime can parse this header to retrieve the appropriate secrets for API calls.

## Best Practices

### Key Naming

- Use descriptive, consistent naming conventions
- Include the service name: `openai_api_key`, `anthropic_token`
- Avoid special characters except underscores
- Keep names under 50 characters for readability

### Secret Management

- Rotate secrets regularly
- Use strong, unique secrets for each service
- Avoid hardcoding secrets in code
- Monitor secret usage and access patterns

### Error Handling

- Always check response status codes
- Handle rate limiting gracefully with exponential backoff
- Log errors for debugging but never log secret values
- Implement proper retry logic for transient failures

### Performance

- Cache connections list when possible (with appropriate TTL)
- Use batch operations when updating multiple connections
- Implement connection pooling for high-volume applications
- Monitor API response times and adjust timeouts accordingly

## Troubleshooting

### Connection Issues

1. **Verify authentication token is valid and not expired**
2. **Check Vault server connectivity and configuration**
3. **Ensure user has proper permissions for the operation**
4. **Verify key_id format and URL encoding**

### Common Problems

- **404 errors**: Check key_id format and user ownership
- **500 errors**: Check Vault server status and logs
- **Rate limiting**: Implement exponential backoff
- **Validation errors**: Verify request data format and constraints

For additional support, check the server logs and Vault audit logs for detailed error information. 