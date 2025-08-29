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

	// Summary state
	let totalConnections = 0;
	let userCountEntries: Array<[string, number]> = [];

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

	// Compute summary reactively
	$: totalConnections = connections.length;
	$: {
		const counts = new Map<string, number>();
		for (const c of connections) {
			const name = c.user_name || $i18n.t('Unknown');
			counts.set(name, (counts.get(name) || 0) + 1);
		}
		userCountEntries = Array.from(counts.entries()).sort((a, b) => {
			if (b[1] !== a[1]) return b[1] - a[1];
			return a[0].localeCompare(b[0]);
		});
	}

	onMount(() => {
		fetchConnections();
	});
</script>

{#if !loading && connections.length > 0}
<div class="mb-4 p-3 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-850">
	<div class="text-sm font-medium text-gray-800 dark:text-gray-200 mb-2">{$i18n.t('Connections Summary')}</div>
	<div class="text-xs text-gray-600 dark:text-gray-400">{$i18n.t('Total connections')}: <span class="font-semibold">{totalConnections}</span></div>
	<div class="mt-2 flex flex-wrap gap-2">
		{#each userCountEntries as [name, count]}
			<span class="px-2 py-1 text-xs rounded-full bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-200 dark:border-gray-700">{name}: {count}</span>
		{/each}
	</div>
</div>
{/if}

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
