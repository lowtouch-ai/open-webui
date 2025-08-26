import { listAgentConnections, type AgentConnection } from '$lib/apis/agent-connections';

// Normalize an agent identifier to underscore format used by the backend
function normalizeAgentId(input?: string | null): string | null {
    if (!input) return null;
    // Take substring before first ':' if present
    const base = input.includes(':') ? input.split(':', 1)[0] : input;
    // Replace runs of non-alphanumeric with single underscore and trim
    const normalized = base.replace(/[^A-Za-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
    return normalized.length ? normalized : 'default';
}

/**
 * Build vault keys header from agent connections
 * @param agentId - Optional agent ID to filter connections
 * @returns Promise<string | null> - Comma-separated vault keys or null if none
 */
export async function buildVaultKeysHeader(agentId?: string): Promise<string | null> {
    try {
        const normAgentId = normalizeAgentId(agentId ?? null);
        console.log('[VaultKeys] buildVaultKeysHeader() called with agentId:', agentId, 'normalized:', normAgentId);
        const token = localStorage.token;
        if (!token) {
            console.log('[VaultKeys] No token found in localStorage; skipping vault keys header');
            return null;
        }

        const connections: AgentConnection[] = await listAgentConnections(token);
        console.log(
            '[VaultKeys] Connections fetched:',
            connections.length,
            connections.map((c) => ({ key_name: c.key_name, agent_id: c.agent_id, is_common: c.is_common }))
        );

        if (connections.length === 0) {
            console.log('[VaultKeys] No agent connections found; skipping vault keys header');
            return null;
        }

        // Filter connections based on agent ID with priority system
        const relevantConnections = connections.filter(conn => {
            // If agent ID is provided, prioritize agent-specific connections
            if (normAgentId) {
                // Include connections specifically for this agent
                if (normalizeAgentId(conn.agent_id ?? null) === normAgentId) return true;
                
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

        console.log(
            '[VaultKeys] Relevant connections:',
            relevantConnections.length,
            relevantConnections.map((c) => ({ key_name: c.key_name, agent_id: c.agent_id, is_common: c.is_common }))
        );

        if (relevantConnections.length === 0) {
            console.log('[VaultKeys] No relevant connections for agentId:', agentId);
            return null;
        }

        // Sort connections to prioritize agent-specific over common
        const sortedConnections = relevantConnections.sort((a, b) => {
            // Agent-specific connections first
            if (normAgentId && normalizeAgentId(a.agent_id ?? null) === normAgentId && normalizeAgentId(b.agent_id ?? null) !== normAgentId) return -1;
            if (normAgentId && normalizeAgentId(b.agent_id ?? null) === normAgentId && normalizeAgentId(a.agent_id ?? null) !== normAgentId) return 1;
            
            // Common connections next
            if (a.is_common && !b.is_common) return 1;
            if (b.is_common && !a.is_common) return -1;
            
            // Alphabetical by key name
            return a.key_name.localeCompare(b.key_name);
        });

        console.log(
            '[VaultKeys] Sorted connections order:',
            sortedConnections.map((c) => ({ key_name: c.key_name, agent_id: c.agent_id, is_common: c.is_common }))
        );

        // Build the header value in format: agent_name/key_name,COMMON/key_name
        const vaultKeys = sortedConnections.map(conn => {
            // Use COMMON prefix for common connections
            if (conn.is_common) {
                return `COMMON/${conn.key_name}`;
            }
            
            // Use agent ID prefix for agent-specific connections
            if (conn.agent_id) {
                const pref = normalizeAgentId(conn.agent_id) ?? normAgentId ?? 'GENERAL';
                return `${pref}/${conn.key_name}`;
            }
            
            // Fallback for legacy connections without agent_id
            const prefix = normAgentId || 'GENERAL';
            return `${prefix}/${conn.key_name}`;
        });

        const headerVal = vaultKeys.join(',');
        console.log('[VaultKeys] Final header value:', headerVal);
        return headerVal;
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

    const _modelId = (model as { id?: unknown })?.id;
    console.log(
        '[VaultKeys] extractAgentIdFromModel:',
        typeof _modelId === 'string' ? _modelId : undefined,
        'resolved agentId:',
        agentId
    );

    if (typeof agentId === 'string') return normalizeAgentId(agentId);

    // Fallback: try to extract from model ID if it follows a pattern
    // e.g., agent:gpt-4 -> agent ID would be "agent"
    if (typeof model.id === 'string' && model.id.includes(':')) {
        const parts = model.id.split(':');
        if (parts.length >= 2) {
            const derived = parts[0];
            console.log(
                '[VaultKeys] extractAgentIdFromModel fallback from id:',
                typeof _modelId === 'string' ? _modelId : undefined,
                '->',
                derived
            );
            return normalizeAgentId(derived);
        }
    }

    return null;
}