<script lang="ts">
	import { onMount, createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { user as userStore } from '$lib/stores';

	const dispatch = createEventDispatcher();

	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ConnectionsTable from './ConnectionsTable.svelte';
	import ConnectionModal from './ConnectionModal.svelte';

	import {
		listAgentConnections,
		createAgentConnection,
		updateAgentConnection,
		deleteAgentConnection,
		type AgentConnection,
		type AgentConnectionCreate,
		type AgentConnectionUpdate
	} from '$lib/apis/agent-connections';

	export let title: string = 'Agent Connections';
	export let showAddButton: boolean = true;
	export let showUserColumn: boolean = false;
	export let connections: AgentConnection[] = [];
	export let loading: boolean = false;
	export let saving: boolean = false;
	export let customFetchConnections: (() => Promise<void>) | null = null;

	let showAddModal = false;
	let editConnection: AgentConnection | null = null;
	let showDeleteConfirmDialog = false;
	let deleteTargetKeyId = '';

	// Simple search (only show for >10 items)
	let searchTerm = '';
	const SEARCH_THRESHOLD = 10;

	$: showSearch = connections.length > SEARCH_THRESHOLD;
	$: filteredConnections = searchTerm.trim() ? connections.filter((c) => {
		const term = searchTerm.trim().toLowerCase();
		return (
			c.key_name.toLowerCase().includes(term) ||
			(c.agent_id || '').toLowerCase().includes(term) ||
			(showUserColumn && c.user_name && c.user_name.toLowerCase().includes(term))
		);
	}) : connections;

	const fetchConnections = async () => {
		if (customFetchConnections) {
			await customFetchConnections();
		} else {
			loading = true;
			try {
				connections = await listAgentConnections($userStore.token);
			} catch (error) {
				console.error('Error fetching agent connections:', error);
				toast.error($i18n.t('Failed to fetch agent connections'));
			} finally {
				loading = false;
			}
		}
	};

	const addConnection = async (connectionData: AgentConnectionCreate) => {
		saving = true;
		try {
			const response = await createAgentConnection($userStore.token, connectionData);
			connections = [...connections, response];
			searchTerm = '';
			toast.success($i18n.t('Agent connection created successfully'));
			dispatch('save');
		} catch (error) {
			console.error('Error creating agent connection:', error);
			toast.error($i18n.t('Failed to create agent connection'));
		} finally {
			saving = false;
		}
	};

	const updateConnectionById = async (updateData: AgentConnectionUpdate, keyId: string) => {
		saving = true;
		try {
			const response = await updateAgentConnection($userStore.token, keyId, updateData);
			
			const index = connections.findIndex(c => c.key_id === keyId);
			if (index !== -1) {
				connections[index] = response;
				connections = [...connections];
			}
			toast.success($i18n.t('Agent connection updated successfully'));
			dispatch('save');
		} catch (error) {
			console.error('Error updating agent connection:', error);
			toast.error($i18n.t('Failed to update agent connection'));
		} finally {
			saving = false;
		}
	};

	const deleteConnectionById = async (keyId: string) => {
		saving = true;
		try {
			await deleteAgentConnection($userStore.token, keyId);
			connections = connections.filter(c => c.key_id !== keyId);
			toast.success($i18n.t('Agent connection deleted successfully'));
			dispatch('save');
		} catch (error) {
			console.error('Error deleting agent connection:', error);
			toast.error($i18n.t('Failed to delete agent connection'));
		} finally {
			saving = false;
		}
	};

	const confirmDelete = (keyId: string) => {
		deleteTargetKeyId = keyId;
		showDeleteConfirmDialog = true;
	};

	const handleDeleteConfirm = () => {
		if (deleteTargetKeyId) {
			deleteConnectionById(deleteTargetKeyId);
			deleteTargetKeyId = '';
		}
		showDeleteConfirmDialog = false;
	};

	onMount(() => {
		fetchConnections();
	});
</script>

<div class="flex flex-col w-full">
	{#if title || showAddButton}
		<div class="flex justify-between items-center mb-4">
			{#if title}
				<div class="text-xl font-bold">{$i18n.t(title)}</div>
			{:else}
				<div></div>
			{/if}
			{#if showAddButton}
				<button
					class="px-3 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
					on:click={() => {
						showAddModal = true;
					}}
				>
					{$i18n.t('Add Connection')}
				</button>
			{/if}
		</div>
	{/if}

	{#if loading}
		<div class="flex justify-center items-center py-8">
			<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-white" />
		</div>
	{:else}
		<!-- Search - Only show for large datasets -->
		{#if showSearch}
			<div class="mb-3 flex justify-between items-center">
				<div class="flex items-center gap-3 w-full">
					<input
						class="w-full md:w-64 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-700 rounded focus:outline-none bg-transparent"
						type="text"
						placeholder={$i18n.t('Search connections...')}
						bind:value={searchTerm}
					/>
					{#if searchTerm}
						<button
							class="px-2 py-1.5 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition"
							on:click={() => { searchTerm = ''; }}
						>
							{$i18n.t('Clear')}
						</button>
					{/if}
				</div>
			</div>
		{/if}

		{#if connections.length === 0}
			<div class="flex flex-col items-center justify-center py-8 text-gray-500">
				<div class="text-lg font-medium mb-2">{$i18n.t('No agent connections')}</div>
				<div class="text-sm">{$i18n.t('Add a connection to get started')}</div>
			</div>
		{:else if filteredConnections.length === 0 && searchTerm}
			<div class="flex flex-col items-center justify-center py-8 text-gray-500">
				<div class="text-lg font-medium mb-2">{$i18n.t('No connections found')}</div>
				<div class="text-sm mb-3">{$i18n.t('No connections match your search criteria')}</div>
				<button
					class="px-3 py-1.5 text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-200 underline transition"
					on:click={() => { searchTerm = ''; }}
				>
					{$i18n.t('Clear search')}
				</button>
			</div>
		{:else}
			<!-- Simple results info -->
			{#if searchTerm}
				<div class="mb-2 text-sm text-gray-600 dark:text-gray-400">
					{$i18n.t('Showing {{count}} of {{total}} connections', { count: filteredConnections.length, total: connections.length })}
				</div>
			{/if}

			<!-- Simple table view -->
			<ConnectionsTable
				connections={filteredConnections}
				{showUserColumn}
				on:edit={(e) => {
					const { index } = e.detail;
					editConnection = { ...filteredConnections[index] };
				}}
				on:delete={(e) => {
					const { index } = e.detail;
					const connection = filteredConnections[index];
					if (connection.key_id) {
						confirmDelete(connection.key_id);
					}
				}}
			/>
		{/if}
	{/if}
</div>

<!-- Modals -->
{#if showAddButton && showAddModal}
	<ConnectionModal
		bind:show={showAddModal}
		mode="add"
		on:save={(e) => addConnection(e.detail.connection)}
	/>
{/if}

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	on:confirm={handleDeleteConfirm}
>
	<div class="text-sm dark:text-gray-300">
		{$i18n.t('Are you sure you want to delete this agent connection? This action cannot be undone.')}
	</div>
</ConfirmDialog>

{#if editConnection}
	<ConnectionModal
		show={true}
		mode="edit"
		connection={editConnection}
		on:close={() => (editConnection = null)}
		on:save={(e) => {
			if (editConnection && editConnection.key_id) {
				updateConnectionById(e.detail.connection, editConnection.key_id);
			}
			editConnection = null;
		}}
		on:delete={() => {
			if (editConnection && editConnection.key_id) {
				confirmDelete(editConnection.key_id);
			}
			editConnection = null;
		}}
	/>
{/if} 