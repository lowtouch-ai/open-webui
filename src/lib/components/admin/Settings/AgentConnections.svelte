<script lang="ts">
	import { onMount, createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { user as userStore } from '$lib/stores';

	const dispatch = createEventDispatcher();

	import AgentConnectionsBase from '$lib/components/common/AgentConnections/AgentConnectionsBase.svelte';

	import {
		listAllAgentConnections,
		type AgentConnection
	} from '$lib/apis/agent-connections';

	export let onSave = () => {};

	let loading = true;
	let connections: AgentConnection[] = [];

	const fetchConnections = async () => {
		loading = true;
		try {
			connections = await listAllAgentConnections($userStore.token);
		} catch (error) {
			console.error('Error fetching agent connections:', error);
			toast.error($i18n.t('Failed to fetch agent connections'));
		} finally {
			loading = false;
		}
	};

	onMount(() => {
		fetchConnections();
	});
</script>

<AgentConnectionsBase 
	title="Agent Connections"
	showAddButton={false}
	showUserColumn={true}
	bind:connections
	bind:loading
	customFetchConnections={fetchConnections}
	on:save={() => {
		onSave();
		dispatch('save');
	}}
/>
