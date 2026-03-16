import { listAgentConnections, type AgentConnection } from '$lib/apis/agent-connections';

/**
 * Sanitize an agent ID to match the agent backend's naming convention.
 * Mirrors the Python: re.sub(r'[^a-zA-Z0-9]', '_', model.split(':')[0])
 * e.g. 'appz/tracker:0.4g' -> 'appz_tracker'
 */
export function sanitizeAgentId(agentId: string): string {
	const base = agentId.split(':')[0];
	return base.replace(/[^a-zA-Z0-9]/g, '_');
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

		// Sanitize the incoming agentId so it matches the sanitized agent_id
		// returned by the backend (which stores sanitized names in Vault)
		const sanitizedAgentId = agentId ? sanitizeAgentId(agentId) : undefined;

		// Filter connections based on agent ID with priority system
		const relevantConnections = connections.filter((conn) => {
			if (sanitizedAgentId) {
				// conn.agent_id is already sanitized by the backend
				if (conn.agent_id === sanitizedAgentId) return true;

				// Include common connections
				if (conn.is_common) return true;

				// Include connections with no agent_id (legacy - available to all)
				if (!conn.agent_id && !conn.is_common) return true;
			} else {
				// No agent ID provided - include common connections and those without agent_id
				if (conn.is_common || !conn.agent_id) return true;
			}

			return false;
		});

		if (relevantConnections.length === 0) return null;

		// Sort connections to prioritize agent-specific over common
		const sortedConnections = relevantConnections.sort((a, b) => {
			// Agent-specific connections first
			if (sanitizedAgentId && a.agent_id === sanitizedAgentId && b.agent_id !== sanitizedAgentId)
				return -1;
			if (sanitizedAgentId && b.agent_id === sanitizedAgentId && a.agent_id !== sanitizedAgentId)
				return 1;

			// Common connections next
			if (a.is_common && !b.is_common) return 1;
			if (b.is_common && !a.is_common) return -1;

			// Alphabetical by key name
			return a.key_name.localeCompare(b.key_name);
		});

		// Build the header value in format expected by agent backend:
		//   agent-specific: sanitized_agent/KEY_NAME
		//   common:         COMMON/KEY_NAME
		const vaultKeys = sortedConnections.map((conn) => {
			if (conn.is_common) {
				return `COMMON/${conn.key_name}`;
			}

			if (conn.agent_id) {
				// conn.agent_id is already sanitized by the backend
				return `${conn.agent_id}/${conn.key_name}`;
			}

			// Fallback for legacy connections without agent_id
			const prefix = sanitizedAgentId || 'GENERAL';
			return `${prefix}/${conn.key_name}`;
		});

		return [...new Set(vaultKeys)].join(',');
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
		(info?.meta as Record<string, unknown>)?.agent_id || meta?.agent_id || model.agent_id;

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
