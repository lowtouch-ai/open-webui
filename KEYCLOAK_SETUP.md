# Setting Up Keycloak as Default Sign-in for Open WebUI

This guide explains how to configure Open WebUI to use Keycloak as the default authentication provider.

## Prerequisites

- Docker and Docker Compose installed
- Basic understanding of Keycloak concepts

## Quick Start with Docker Compose

1. Use the provided `docker-compose.keycloak.yml` file to start Open WebUI with Keycloak integration:

```bash
docker-compose -f docker-compose.keycloak.yml up -d
```

This will start:
- Open WebUI on port 8080
- Ollama on port 11434
- Keycloak on port 8081
- PostgreSQL database for Keycloak

## Keycloak Configuration

After starting the services, you need to configure Keycloak:

1. Access the Keycloak admin console at http://localhost:8081/admin/
2. Log in with the default credentials:
   - Username: `admin`
   - Password: `admin`

3. Create a new realm:
   - Click on the dropdown in the top-left corner (shows "master" by default)
   - Click "Create Realm"
   - Name it `open-webui`
   - Click "Create"

4. Create a new client:
   - Go to "Clients" in the left sidebar
   - Click "Create client"
   - Set Client ID to `open-webui-client`
   - Enable "Client authentication"
   - Set "Root URL" to `http://localhost:8080`
   - Set "Valid redirect URIs" to `http://localhost:8080/*`
   - Set "Web origins" to `http://localhost:8080`
   - Click "Save"

5. Get the client secret:
   - Go to the "Credentials" tab of your client
   - Copy the client secret
   - Update the `KEYCLOAK_CLIENT_SECRET` in your docker-compose.keycloak.yml file

6. Create roles:
   - Go to "Realm roles" in the left sidebar
   - Click "Create role"
   - Create roles named `user` and `admin`

7. Create a user:
   - Go to "Users" in the left sidebar
   - Click "Add user"
   - Fill in the details and click "Create"
   - Go to the "Credentials" tab and set a password
   - Go to the "Role mappings" tab and assign the appropriate roles

8. Restart the Open WebUI container to apply the updated client secret:
```bash
docker-compose -f docker-compose.keycloak.yml restart open-webui
```

## Environment Variables

The following environment variables are used to configure Keycloak integration:

| Variable | Description |
|----------|-------------|
| `KEYCLOAK_ENABLED` | Set to `true` to enable Keycloak integration |
| `KEYCLOAK_SERVER_URL` | URL of the Keycloak server |
| `KEYCLOAK_REALM` | Keycloak realm name |
| `KEYCLOAK_CLIENT_ID` | Client ID for the Open WebUI application |
| `KEYCLOAK_CLIENT_SECRET` | Client secret for the Open WebUI application |
| `KEYCLOAK_REDIRECT_URI` | Redirect URI after successful authentication |

## OAuth Configuration

These variables configure how OAuth works with Keycloak:

| Variable | Description |
|----------|-------------|
| `OAUTH_PROVIDER_NAME` | Display name for the OAuth provider |
| `OAUTH_SCOPES` | OAuth scopes to request |
| `OAUTH_EMAIL_CLAIM` | Claim to use for the user's email |
| `OAUTH_USERNAME_CLAIM` | Claim to use for the username |
| `OAUTH_PICTURE_CLAIM` | Claim to use for the profile picture |
| `OAUTH_ROLES_CLAIM` | Claim to use for roles |
| `OAUTH_GROUPS_CLAIM` | Claim to use for groups |
| `ENABLE_OAUTH_SIGNUP` | Allow new users to sign up via OAuth |
| `OAUTH_MERGE_ACCOUNTS_BY_EMAIL` | Merge accounts with the same email |
| `ENABLE_OAUTH_ROLE_MANAGEMENT` | Enable role-based access control |
| `ENABLE_OAUTH_GROUP_MANAGEMENT` | Enable group-based access control |
| `OAUTH_ALLOWED_ROLES` | Roles that are allowed to access the application |
| `OAUTH_ADMIN_ROLES` | Roles that are granted admin privileges |

## Usage

Once configured, when users access Open WebUI, they will be automatically redirected to the Keycloak login page. After successful authentication, they will be redirected back to Open WebUI.

## Troubleshooting

- If you encounter issues with the redirect URI, make sure it matches exactly what is configured in Keycloak
- Check the logs of the Open WebUI container for any error messages
- Ensure the Keycloak client has the correct settings for client authentication and redirect URIs
