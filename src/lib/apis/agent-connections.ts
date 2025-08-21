import { WEBUI_BASE_URL } from '../constants';

export interface AgentConnection {
	name: string;
	value: string;
	agent_id?: string;
	is_common: boolean;
}

export interface AgentConnectionsConfig {
	AGENT_CONNECTIONS: AgentConnection[];
}

export const getAgentConnectionsConfig = async (token: string) => {
	const response = await fetch(`${WEBUI_BASE_URL}/api/v1/configs/agent_connections`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});

	if (!response.ok) {
		throw new Error(`Failed to get agent connections config: ${response.statusText}`);
	}

	return await response.json();
};

export const setAgentConnectionsConfig = async (
	token: string,
	config: AgentConnectionsConfig
) => {
	const response = await fetch(`${WEBUI_BASE_URL}/api/v1/configs/agent_connections`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(config)
	});

	if (!response.ok) {
		throw new Error(`Failed to set agent connections config: ${response.statusText}`);
	}

	return await response.json();
};
