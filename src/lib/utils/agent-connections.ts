import { get } from 'svelte/store';
import { user } from '$lib/stores';
import { getAgentConnectionsConfig, type AgentConnection } from '$lib/apis/agent-connections';

/**
 * Build vault keys header from agent connections
 * @param agentId - Optional agent ID to filter connections
 * @returns Promise<string | null> - Comma-separated vault keys or null if none
 */
export async function buildVaultKeysHeader(agentId?: string): Promise<string | null> {
	try {
		const token = localStorage.token;
		if (!token) return null;

		const response = await getAgentConnectionsConfig(token);
		const connections: AgentConnection[] = response.AGENT_CONNECTIONS || [];

		if (connections.length === 0) return null;

		// Filter connections based on agent ID
		const relevantConnections = connections.filter(conn => {
			// Include common connections
			if (conn.is_common) return true;
			
			// Include connections for specific agent
			if (agentId && conn.agent_id === agentId) return true;
			
			// Include connections with no agent_id (available to all)
			if (!conn.agent_id) return true;
			
			return false;
		});

		if (relevantConnections.length === 0) return null;

		// Build the header value in format: agentId_key1,COMMON_key2
		const vaultKeys = relevantConnections.map(conn => {
			const prefix = conn.is_common ? 'COMMON' : (agentId || 'UNKNOWN');
			return `${prefix}_${conn.name}`;
		});

		return vaultKeys.join(',');
	} catch (error) {
		console.error('Error building vault keys header:', error);
		return null;
	}
}

/**
 * Extract agent ID from model info
 * @param model - Model object from the store
 * @returns string | null - Agent ID if found
 */
export function extractAgentIdFromModel(model: any): string | null {
	if (!model) return null;

	// Check model meta for agent_id
	const agentId = model.info?.meta?.agent_id || 
					model.meta?.agent_id || 
					model.agent_id;

	if (agentId) return agentId;

	// Fallback: try to extract from model ID if it follows a pattern
	// e.g., agent:gpt-4 -> agent ID would be "agent"
	if (typeof model.id === 'string' && model.id.includes(':')) {
		const parts = model.id.split(':');
		if (parts.length >= 2) {
			return parts[0];
		}
	}

	return null;
} 