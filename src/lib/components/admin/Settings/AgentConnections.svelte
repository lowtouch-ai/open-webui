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

// Search & pagination
let searchTerm = '';
const pageSize = 10;
let currentPage = 1;

$: filteredConnections = agentConnections.filter((c) => {
	const term = searchTerm.trim().toLowerCase();
	if (!term) return true;
	return (
		c.name.toLowerCase().includes(term) ||
		(c.agent_id || '').toLowerCase().includes(term)
	);
});

$: totalPages = Math.max(1, Math.ceil(filteredConnections.length / pageSize));
$: paginatedConnections = filteredConnections.slice((currentPage - 1) * pageSize, currentPage * pageSize);

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
	{:else if filteredConnections.length === 0}
		<div class="flex flex-col items-center justify-center py-8 text-gray-500">
			<div class="text-lg font-medium mb-2">{$i18n.t('No agent connections')}</div>
			<div class="text-sm">{$i18n.t('Add a connection to get started')}</div>
		</div>
	{:else}
		<!-- Search filter -->
		<div class="mb-3 flex justify-between items-center">
			<input
				class="w-full md:w-64 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-700 rounded focus:outline-none bg-transparent"
				type="text"
				placeholder={$i18n.t('Search')}
				bind:value={searchTerm}
		/>
		</div>

		<!-- Table view of connections -->
		<ConnectionsTable
			connections={paginatedConnections}
			on:edit={(e) => {
				const { index } = e.detail;
				editConnection = paginatedConnections[index];
			}}
			on:delete={(e) => {
				const { index } = e.detail;
				// Need original index in agentConnections array
				const globalIndex = agentConnections.indexOf(paginatedConnections[index]);
				if (globalIndex !== -1) deleteConnection(globalIndex);
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
</div>

<!-- Add/Edit Modals -->
{#if showAddModal}
	<ConnectionModal
		bind:show={showAddModal}
		mode="add"
		on:save={(e) => addConnection(e.detail.connection)}
	/>
{/if}
<Modal size="sm" bind:show={showAddModal}>
	<div>
		<div class="flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
			<div class="text-lg font-medium self-center font-primary">
				{$i18n.t('Add Agent Connection')}
			</div>
			<button
				class="self-center"
				on:click={() => {
					showAddModal = false;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-4 pb-4 md:space-x-4 dark:text-gray-200">
			<div class="flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit={(e) => {
						e.preventDefault();
						
						if (!name) {
							toast.error($i18n.t('Name is required'));
							return;
						}

						if (!validateConnectionName(name)) {
							toast.error($i18n.t('Name must be alphanumeric with no spaces'));
							return;
						}

						if (!value) {
							toast.error($i18n.t('Value is required'));
							return;
						}

						addConnection({
							name,
							value,
							agent_id: agent_id || null,
							is_common
						});

						name = '';
						value = '';
						agent_id = '';
						is_common = false;
						showAddModal = false;
					}}
				>
					<div class="px-1">
						<div class="flex flex-col w-full mb-2">
							<div class="mb-0.5 text-xs text-gray-500">{$i18n.t('Name')}</div>

							<div class="flex-1">
								<input
									class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
									type="text"
									bind:value={name}
									placeholder={$i18n.t('Connection Name')}
									autocomplete="off"
									required
								/>
							</div>
						</div>

						<div class="flex flex-col w-full mb-2">
							<div class="mb-0.5 text-xs text-gray-500">{$i18n.t('Value')}</div>

							<div class="flex-1">
								<SensitiveInput
									className="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
									bind:value={value}
									placeholder={$i18n.t('Connection Value')}
									required={true}
								/>
							</div>
						</div>

						<div class="flex flex-col w-full mb-2">
							<div class="mb-0.5 text-xs text-gray-500">{$i18n.t('Agent ID (Optional)')}</div>

							<div class="flex-1">
								<input
									class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
									type="text"
									bind:value={agent_id}
									placeholder={$i18n.t('Leave empty for common connections')}
									autocomplete="off"
								/>
							</div>
						</div>

						<div class="flex items-center mb-2">
							<div class="text-xs text-gray-500 mr-2">{$i18n.t('Common Connection')}</div>
							<Tooltip
								content={is_common
									? $i18n.t('This connection is available to all agents')
									: $i18n.t('This connection is specific to an agent')}
							>
								<Switch bind:state={is_common} />
							</Tooltip>
						</div>
					</div>

					<div class="flex justify-end pt-3 text-sm font-medium">
						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center"
							type="submit"
						>
							{$i18n.t('Save')}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>

{#if editConnection}
	<ConnectionModal
		show={true}
		mode="edit"
		connection={editConnection}
		on:close={() => (editConnection = null)}
		on:save={(e) => {
			const idx = agentConnections.indexOf(editConnection);
			if (idx !== -1) updateConnection(e.detail.connection, idx);
			editConnection = null;
		}}
		on:delete={() => {
			const idx = agentConnections.indexOf(editConnection);
			if (idx !== -1) deleteConnection(idx);
			editConnection = null;
		}}
	/>
{/if}
