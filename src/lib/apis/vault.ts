/**
 * Interface for Vault configuration with optional fields
 * Used for partial updates
 */
export interface VaultConfig {
	ENABLE_VAULT_INTEGRATION?: boolean;
	VAULT_URL?: string;
	VAULT_TOKEN?: string;
	VAULT_MOUNT_PATH?: string;
	VAULT_TIMEOUT?: number;
	VAULT_VERIFY_SSL?: boolean;
}

/**
 * Interface for complete Vault configuration form
 * Used for API responses
 */
export interface VaultConfigForm {
    ENABLE_VAULT_INTEGRATION: boolean;
    VAULT_URL: string;
    VAULT_TOKEN: string;
    VAULT_MOUNT_PATH: string;
    VAULT_TIMEOUT: number;
    VAULT_VERIFY_SSL: boolean;
}

/**
 * Interface for Vault connection test result
 */
export interface VaultConnectionTestResult {
    success: boolean;
    message: string;
}
