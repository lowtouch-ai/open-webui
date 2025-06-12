import { WEBUI_BASE_URL } from '$lib/constants';

/**
 * Interface for Vault configuration with optional fields
 * Used for partial updates
 */
export interface VaultConfig {
	ENABLE_VAULT_INTEGRATION?: boolean;
	VAULT_URL?: string;
	VAULT_TOKEN?: string;
	VAULT_MOUNT_PATH?: string;
	VAULT_KV_VERSION?: number;
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
    VAULT_KV_VERSION: number;
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

/**
 * Get the current Vault configuration
 * @param token Authentication token
 * @returns Promise resolving to the Vault configuration
 */
export const getVaultConfig = async (token: string = ''): Promise<VaultConfigForm> => {
    try {
        const response = await fetch(`${WEBUI_BASE_URL}/api/vault/config`, {
            method: 'GET',
            headers: {
                Accept: 'application/json',
                'Content-Type': 'application/json',
                ...(token && { authorization: `Bearer ${token}` })
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw errorData;
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error fetching Vault config:', error);
        throw error;
    }
};

/**
 * Update the Vault configuration
 * @param token Authentication token
 * @param config Vault configuration to set
 * @returns Promise resolving to the updated Vault configuration
 */
export const setVaultConfig = async (token: string = '', config: VaultConfig): Promise<VaultConfigForm> => {
    try {
        const response = await fetch(`${WEBUI_BASE_URL}/api/vault/config`, {
            method: 'POST',
            headers: {
                Accept: 'application/json',
                'Content-Type': 'application/json',
                ...(token && { authorization: `Bearer ${token}` })
            },
            body: JSON.stringify(config)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw errorData;
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error setting Vault config:', error);
        throw error;
    }
};

/**
 * Test the Vault connection with current configuration
 * @param token Authentication token
 * @returns Promise resolving to the test result with success status and message
 */
export const testVaultConnection = async (token: string = ''): Promise<VaultConnectionTestResult> => {
    try {
        const response = await fetch(`${WEBUI_BASE_URL}/api/vault/test_connection`, {
            method: 'GET',
            headers: {
                Accept: 'application/json',
                'Content-Type': 'application/json',
                ...(token && { authorization: `Bearer ${token}` })
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw errorData;
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error testing Vault connection:', error);
        throw error;
    }
};
