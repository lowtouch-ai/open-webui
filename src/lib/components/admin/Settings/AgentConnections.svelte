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
	let agentCountEntries: Array<[string, number]> = [];
	let scopeCountEntries: Array<[string, number]> = [];

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
		const userCounts = new Map<string, number>();
		const agentCounts = new Map<string, number>();
		let common = 0;
		let scoped = 0;
		for (const c of connections) {
			const uname = c.user_name || $i18n.t('Unknown');
			userCounts.set(uname, (userCounts.get(uname) || 0) + 1);
			const agent = c.agent_id && c.agent_id.length > 0 ? c.agent_id : $i18n.t('Unassigned');
			agentCounts.set(agent, (agentCounts.get(agent) || 0) + 1);
			if (c.is_common) common += 1; else scoped += 1;
		}
		userCountEntries = Array.from(userCounts.entries()).sort((a, b) => {
			if (b[1] !== a[1]) return b[1] - a[1];
			return a[0].localeCompare(b[0]);
		});
		agentCountEntries = Array.from(agentCounts.entries()).sort((a, b) => {
			if (b[1] !== a[1]) return b[1] - a[1];
			return a[0].localeCompare(b[0]);
		});
		const commonLabel = $i18n.t('Common');
		const scopedLabel = $i18n.t('Scoped');
		scopeCountEntries = [
			[commonLabel, common],
			[scopedLabel, scoped]
		];
	}

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


{#if !loading && connections.length > 0}

<hr class=" border-gray-100 dark:border-gray-700/10 my-2.5 w-full" />


<div class="mt-4 p-4 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-850">
	<div class="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-3">{$i18n.t('Connections Summary')}</div>
	<div class="text-xs text-gray-600 dark:text-gray-400 mb-3">{$i18n.t('Total connections')}: <span class="font-semibold">{totalConnections}</span></div>
	<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
		<div>
			<div class="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">{$i18n.t('By User')}</div>
			<div class="flex flex-wrap gap-2">
				{#each userCountEntries as [name, count]}
					<span class="px-2 py-1 text-xs rounded-full bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-200 dark:border-gray-700">{name}: {count}</span>
				{/each}
			</div>
		</div>
		<div>
			<div class="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">{$i18n.t('By Model')}</div>
			<div class="flex flex-wrap gap-2">
				{#each agentCountEntries as [agent, count]}
					<span class="px-2 py-1 text-xs rounded-full bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-200 dark:border-gray-700">{agent}: {count}</span>
				{/each}
			</div>
		</div>
		<div>
			<div class="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">{$i18n.t('By Scope')}</div>
			<div class="flex flex-wrap gap-2">
				{#each scopeCountEntries as [scope, count]}
					<span class="px-2 py-1 text-xs rounded-full bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 border border-gray-200 dark:border-gray-700">{scope}: {count}</span>
				{/each}
			</div>
		</div>
	</div>
</div>
{/if}
