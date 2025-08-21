import { WEBUI_BASE_URL } from '../constants';

export interface AgentConnection {
	key_id: string;
	key_name: string;
	agent_id?: string;
	is_common: boolean;
	created_at: string;
	user_id?: string;
	user_name?: string;
	user_email?: string;
}

export interface AgentConnectionCreate {
	key_name: string;
	key_value: string;
	agent_id?: string;
	is_common: boolean;
}

export interface AgentConnectionUpdate {
	key_name?: string;
	key_value?: string;
	agent_id?: string;
	is_common?: boolean;
}

export const getAgentConnectionsStatus = async (token: string) => {
	const response = await fetch(`${WEBUI_BASE_URL}/api/v1/agent_connections/status`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});

	if (!response.ok) {
		throw new Error(`Failed to get agent connections status: ${response.statusText}`);
	}

	return await response.json();
};

// REST API functions
export const createAgentConnection = async (
	token: string,
	connection: AgentConnectionCreate
) => {
	const response = await fetch(`${WEBUI_BASE_URL}/api/v1/agent_connections/`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(connection)
	});

	if (!response.ok) {
		throw new Error(`Failed to create agent connection: ${response.statusText}`);
	}

	return await response.json();
};

export const listAgentConnections = async (token: string): Promise<AgentConnection[]> => {
	const response = await fetch(`${WEBUI_BASE_URL}/api/v1/agent_connections/`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});

	if (!response.ok) {
		throw new Error(`Failed to list agent connections: ${response.statusText}`);
	}

	return await response.json();
};

export const listAllAgentConnections = async (token: string): Promise<AgentConnection[]> => {
	const response = await fetch(`${WEBUI_BASE_URL}/api/v1/agent_connections/admin/all`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});

	if (!response.ok) {
		throw new Error(`Failed to list all agent connections: ${response.statusText}`);
	}

	return await response.json();
};

export const getAgentConnection = async (token: string, keyId: string) => {
	const response = await fetch(`${WEBUI_BASE_URL}/api/v1/agent_connections/${keyId}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});

	if (!response.ok) {
		throw new Error(`Failed to get agent connection: ${response.statusText}`);
	}

	return await response.json();
};

export const updateAgentConnection = async (
	token: string,
	keyId: string,
	connection: AgentConnectionUpdate
) => {
	const response = await fetch(`${WEBUI_BASE_URL}/api/v1/agent_connections/${keyId}`, {
		method: 'PUT',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(connection)
	});

	if (!response.ok) {
		throw new Error(`Failed to update agent connection: ${response.statusText}`);
	}

	return await response.json();
};

export const deleteAgentConnection = async (token: string, keyId: string) => {
	const response = await fetch(`${WEBUI_BASE_URL}/api/v1/agent_connections/${keyId}`, {
		method: 'DELETE',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});

	if (!response.ok) {
		throw new Error(`Failed to delete agent connection: ${response.statusText}`);
	}

	return await response.json();
};
