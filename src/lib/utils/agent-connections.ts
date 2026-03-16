import { listAgentConnections, type AgentConnection } from '$lib/apis/agent-connections';

/**
 * Sanitize an agent ID to match the backend's Vault path component format.
 * Replaces any non-alphanumeric character with '_', identical to the agent
 * backend derivation and vault.py's sanitize_agent_id().
 */
function sanitizeAgentId(id: string): string {
	return id.replace(/[^a-zA-Z0-9]/g, '_');
}

/**
 * Build vault keys header from agent connections
 * @param agentId - Optional agent ID to filter connections
 * @returns Promise<string | null> - Comma-separated vault keys or null if none
 */
export async function buildVaultKeysHeader(agentId?: string): Promise<string | null> {
	try {
		const token = localStorage.token;
		if (!token) return null;

		const connections: AgentConnection[] = await listAgentConnections(token);

		if (connections.length === 0) return null;

		// The backend returns agent_id as the sanitized Vault folder name (e.g. "appz_tracker").
		// Compare against the sanitized form of the incoming agentId.
		const sanitizedAgentId = agentId ? sanitizeAgentId(agentId) : undefined;

		// Filter connections based on agent ID with priority system
		const relevantConnections = connections.filter(conn => {
			if (sanitizedAgentId) {
				if (conn.agent_id === sanitizedAgentId) return true;
				if (conn.is_common) return true;
				if (!conn.agent_id && !conn.is_common) return true;
			} else {
				if (conn.is_common || !conn.agent_id) return true;
			}
			return false;
		});

		if (relevantConnections.length === 0) return null;

		// Sort: agent-specific first, then common, then alphabetical
		const sortedConnections = relevantConnections.sort((a, b) => {
			if (sanitizedAgentId && a.agent_id === sanitizedAgentId && b.agent_id !== sanitizedAgentId) return -1;
			if (sanitizedAgentId && b.agent_id === sanitizedAgentId && a.agent_id !== sanitizedAgentId) return 1;
			if (a.is_common && !b.is_common) return 1;
			if (b.is_common && !a.is_common) return -1;
			return a.key_name.localeCompare(b.key_name);
		});

		// Build header value: "{sanitized_agent}/{key_name}" or "^{key_name}" for COMMON.
		// The backend's sanitize_vault_keys_header() handles the "/" format correctly (Case 2).
		const vaultKeys = sortedConnections.map(conn => {
			if (conn.is_common) {
				return `^${conn.key_name}`;
			}
			if (conn.agent_id) {
				return `${conn.agent_id}/${conn.key_name}`;
			}
			const prefix = sanitizedAgentId || 'GENERAL';
			return `${prefix}/${conn.key_name}`;
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
export function extractAgentIdFromModel(model: Record<string, unknown>): string | null {
	if (!model) return null;

	// Check model meta for agent_id
	const info = model.info as Record<string, unknown> | undefined;
	const meta = model.meta as Record<string, unknown> | undefined;
	
	const agentId = 
		(info?.meta as Record<string, unknown>)?.agent_id || 
		meta?.agent_id || 
		model.agent_id;

	if (typeof agentId === 'string') return agentId;

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