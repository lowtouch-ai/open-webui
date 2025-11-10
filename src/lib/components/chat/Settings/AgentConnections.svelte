<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import AgentConnectionsBase from '$lib/components/common/AgentConnections/AgentConnectionsBase.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let saveSettings: Function;
</script>

<form
	id="tab-agent-connections"
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		dispatch('save');
	}}
>
	<div class="py-1 overflow-y-scroll max-h-[28rem] lg:max-h-full">
		<div class="text-sm text-gray-600 dark:text-gray-400 mb-3">
			{$i18n.t('Manage your personal agent connections and API keys. These connections are private to your account.')}
		</div>

		<AgentConnectionsBase 
			title=""
			showAddButton={true}
			showUserColumn={false}
			on:save={() => {
				toast.success($i18n.t('Agent connection saved successfully!'));
			}}
		/>
	</div>
</form> 