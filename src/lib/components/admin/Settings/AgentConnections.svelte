<script lang="ts">
	import { onMount, createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { user as userStore } from '$lib/stores';
	import { config as configStore } from '$lib/stores';

	const dispatch = createEventDispatcher();

	import Modal from '$lib/components/common/Modal.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ConnectionsTable from './AgentConnections/ConnectionsTable.svelte';
	import ConnectionModal from './AgentConnections/ConnectionModal.svelte';

	import {
		getAgentConnectionsConfig,
		setAgentConnectionsConfig,
		type AgentConnection
	} from '$lib/apis/agent-connections';

	export let onSave = () => {};

	let loading = true;
	let saving = false;

	let agentConnections: AgentConnection[] = [];
	let showAddModal = false;
	let editConnection: AgentConnection | null = null;
	let showDeleteConfirmDialog = false;
	let deleteTargetIndex = -1;

// Search & pagination
let searchTerm = '';
const pageSize = 10;
let currentPage = 1;

$: filteredConnections = agentConnections.filter((c) => {
	const term = searchTerm.trim().toLowerCase();
	if (!term) return true;
	return (
		c.name.toLowerCase().includes(term) ||
		(c.agent_id || '').toLowerCase().includes(term) ||
		(c.value || '').toLowerCase().includes(term)
	);
});

$: totalPages = Math.max(1, Math.ceil(filteredConnections.length / pageSize));
$: paginatedConnections = filteredConnections.slice((currentPage - 1) * pageSize, currentPage * pageSize);

// Reset to first page when search results change
$: if (searchTerm !== undefined) {
	currentPage = 1;
}

function goToPage(p: number) {
	currentPage = Math.min(Math.max(1, p), totalPages);
}

	// Variables for add modal
	let name = '';
	let value = '';
	let agent_id = '';
	let is_common = false;

	// Variables for edit modal
	$: editName = editConnection?.name || '';
	$: editValue = editConnection?.value || '';
	$: editAgentId = editConnection?.agent_id || '';
	$: editIsCommon = editConnection?.is_common || false;

	const fetchConfig = async () => {
		loading = true;

		try {
			const response = await getAgentConnectionsConfig($userStore.token);
			agentConnections = response.AGENT_CONNECTIONS || [];
		} catch (error) {
			console.error('Error fetching agent connections config:', error);
			toast.error($i18n.t('Failed to fetch agent connections config'));
		} finally {
			loading = false;
		}
	};

	const saveConfig = async () => {
		saving = true;

		try {
			await setAgentConnectionsConfig($userStore.token, {
				AGENT_CONNECTIONS: agentConnections
			});

			toast.success($i18n.t('Agent connections config saved successfully'));
			dispatch('save');
		} catch (error) {
			console.error('Error saving agent connections config:', error);
			toast.error($i18n.t('Failed to save agent connections config'));
		} finally {
			saving = false;
		}
	};

	// Validate connection name (alphanumeric, no spaces)
	const validateConnectionName = (name: string): boolean => {
		return /^[a-zA-Z0-9_]+$/.test(name);
	};

	const addConnection = (connection: AgentConnection) => {
		agentConnections = [...agentConnections, connection];
		// Reset search to show the newly added connection
		searchTerm = '';
		currentPage = 1;
		saveConfig();
	};

	const updateConnection = (connection: AgentConnection, index: number) => {
		agentConnections[index] = connection;
		agentConnections = [...agentConnections];
		saveConfig();
	};

	const deleteConnection = (index: number) => {
		agentConnections.splice(index, 1);
		agentConnections = [...agentConnections];
		saveConfig();
	};

	const confirmDelete = (index: number) => {
		deleteTargetIndex = index;
		showDeleteConfirmDialog = true;
	};

	const handleDeleteConfirm = () => {
		if (deleteTargetIndex !== -1) {
			deleteConnection(deleteTargetIndex);
			deleteTargetIndex = -1;
		}
		showDeleteConfirmDialog = false;
	};

	onMount(() => {
		fetchConfig();
	});
</script>

<div class="flex flex-col w-full">
	<div class="flex justify-between items-center mb-4">
		<div class="text-xl font-bold">{$i18n.t('Agent Connections')}</div>
		<button
			class="px-3 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			on:click={() => {
				showAddModal = true;
			}}
		>
			{$i18n.t('Add Connection')}
		</button>
	</div>

	{#if loading}
		<div class="flex justify-center items-center py-8">
			<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-white" />
		</div>
	{:else}
		<!-- Search filter - Always show when there are connections -->
		{#if agentConnections.length > 0}
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

		{#if agentConnections.length === 0}
			<!-- No connections at all -->
			<div class="flex flex-col items-center justify-center py-8 text-gray-500">
				<div class="text-lg font-medium mb-2">{$i18n.t('No agent connections')}</div>
				<div class="text-sm">{$i18n.t('Add a connection to get started')}</div>
			</div>
		{:else if filteredConnections.length === 0}
			<!-- No search results -->
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
			<!-- Results info -->
			<div class="mb-2 text-sm text-gray-600 dark:text-gray-400">
				{#if searchTerm}
					{$i18n.t('Showing {{count}} of {{total}} connections', { count: filteredConnections.length, total: agentConnections.length })}
				{:else}
					{$i18n.t('Showing {{count}} connections', { count: agentConnections.length })}
				{/if}
			</div>

			<!-- Table view of connections -->
			<ConnectionsTable
			connections={paginatedConnections}
			on:edit={(e) => {
				const { index } = e.detail;
				editConnection = paginatedConnections[index];
				// Store the original index for reliable updates
				editConnection._originalIndex = agentConnections.findIndex(conn => 
					conn.name === editConnection.name && 
					conn.value === editConnection.value && 
					conn.agent_id === editConnection.agent_id
				);
			}}
			on:delete={(e) => {
				const { index } = e.detail;
				// Need original index in agentConnections array
				const globalIndex = agentConnections.findIndex(conn => {
					const target = paginatedConnections[index];
					return conn.name === target.name && 
						   conn.value === target.value && 
						   conn.agent_id === target.agent_id;
				});
				if (globalIndex !== -1) confirmDelete(globalIndex);
			}}
		/>

			<!-- Pagination controls -->
			{#if totalPages > 1}
				<div class="flex justify-center mt-4 space-x-2 text-sm">
					<button
						class="px-2 py-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-40"
						disabled={currentPage === 1}
						on:click={() => goToPage(currentPage - 1)}
					>
						Prev
					</button>
					{#each Array(totalPages) as _, i}
						<button
							class="px-2 py-1 rounded {currentPage === i + 1 ? 'bg-gray-300 dark:bg-gray-600 font-semibold' : 'hover:bg-gray-200 dark:hover:bg-gray-700'}"
							on:click={() => goToPage(i + 1)}
						>
							{i + 1}
						</button>
					{/each}
					<button
						class="px-2 py-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-40"
						disabled={currentPage === totalPages}
						on:click={() => goToPage(currentPage + 1)}
					>
						Next
					</button>
				</div>
			{/if}
		{/if}
	{/if}
</div>

<!-- Add/Edit Modals -->
{#if showAddModal}
	<ConnectionModal
		bind:show={showAddModal}
		mode="add"
		on:save={(e) => addConnection(e.detail.connection)}
	/>
{/if}

<!-- Delete Confirmation Dialog -->
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
			// Use the stored original index if available, otherwise fall back to findIndex
			let idx = editConnection._originalIndex;
			if (idx === undefined || idx === -1) {
				idx = agentConnections.findIndex(conn => 
					conn.name === editConnection.name && 
					conn.value === editConnection.value && 
					conn.agent_id === editConnection.agent_id
				);
			}
			if (idx !== -1) updateConnection(e.detail.connection, idx);
			editConnection = null;
		}}
		on:delete={() => {
			// Use the stored original index if available, otherwise fall back to findIndex  
			let idx = editConnection._originalIndex;
			if (idx === undefined || idx === -1) {
				idx = agentConnections.findIndex(conn => 
					conn.name === editConnection.name && 
					conn.value === editConnection.value && 
					conn.agent_id === editConnection.agent_id
				);
			}
			if (idx !== -1) confirmDelete(idx);
			editConnection = null;
		}}
	/>
{/if}
