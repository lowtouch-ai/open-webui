<script lang="ts">
	import { getContext } from 'svelte';
	import { user } from '$lib/stores';
	import AgentConnectionsBase from '$lib/components/common/AgentConnections/AgentConnectionsBase.svelte';

	const i18n = getContext('i18n');
</script>

<svelte:head>
	<title>{$i18n.t('Agent Connections')} • Open WebUI</title>
</svelte:head>

<div class="h-full flex flex-col space-y-1">
	<div class="px-2.5 flex justify-between space-y-1">
		<div class="flex flex-col">
			<div class="text-2xl font-semibold">{$i18n.t('Agent Connections')}</div>
			<div class="text-sm text-gray-500 dark:text-gray-400">
				{$i18n.t('Manage your personal agent connections and API keys')}
			</div>
		</div>
	</div>

	<div class="flex-1 px-2.5 py-1">
		<AgentConnectionsBase 
			title="My Agent Connections"
			showAddButton={true}
			showUserColumn={false}
		/>
	</div>
</div> 