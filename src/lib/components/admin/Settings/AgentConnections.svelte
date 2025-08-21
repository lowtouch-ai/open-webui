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
	{:else if agentConnections.length === 0}
		<div class="flex flex-col items-center justify-center py-8 text-gray-500">
			<div class="text-lg font-medium mb-2">{$i18n.t('No agent connections')}</div>
			<div class="text-sm">{$i18n.t('Add a connection to get started')}</div>
		</div>
	{:else}
		<div class="grid grid-cols-1 gap-4">
			{#each agentConnections as connection, i}
				<div
					class="flex flex-col md:flex-row justify-between items-start md:items-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg"
				>
					<div class="flex flex-col">
						<div class="font-medium">{connection.name}</div>
						<div class="text-sm text-gray-500">
							{#if connection.is_common}
								{$i18n.t('Common Connection')}
							{:else if connection.agent_id}
								{$i18n.t('Agent')}: {connection.agent_id}
							{:else}
								{$i18n.t('Unassigned Connection')}
							{/if}
						</div>
					</div>
					<div class="flex mt-2 md:mt-0">
						<button
							class="px-3 py-1.5 text-sm font-medium bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 transition rounded-full mr-2"
							on:click={() => {
								editConnection = connection;
							}}
						>
							{$i18n.t('Edit')}
						</button>
						<button
							class="px-3 py-1.5 text-sm font-medium bg-red-100 hover:bg-red-200 text-red-700 dark:bg-red-900 dark:hover:bg-red-800 dark:text-red-100 transition rounded-full"
							on:click={() => {
								deleteConnection(i);
							}}
						>
							{$i18n.t('Delete')}
						</button>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<!-- Add Connection Modal -->
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

<!-- Edit Connection Modal -->
{#if editConnection}
	<Modal
		size="sm"
		show={!!editConnection}
		on:close={() => {
			editConnection = null;
		}}
	>
		<div>
			<div class="flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
				<div class="text-lg font-medium self-center font-primary">
					{$i18n.t('Edit Agent Connection')}
				</div>
				<button
					class="self-center"
					on:click={() => {
						editConnection = null;
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
							
							if (!editName) {
								toast.error($i18n.t('Name is required'));
								return;
							}

							if (!validateConnectionName(editName)) {
								toast.error($i18n.t('Name must be alphanumeric with no spaces'));
								return;
							}

							if (!editValue) {
								toast.error($i18n.t('Value is required'));
								return;
							}

							const index = agentConnections.findIndex((c) => c === editConnection);
							if (index !== -1) {
								updateConnection({
									name: editName,
									value: editValue,
									agent_id: editAgentId || null,
									is_common: editIsCommon
								}, index);
							}

							editConnection = null;
						}}
					>
						<div class="px-1">
							<div class="flex flex-col w-full mb-2">
								<div class="mb-0.5 text-xs text-gray-500">{$i18n.t('Name')}</div>

								<div class="flex-1">
									<input
										class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
										type="text"
										bind:value={editName}
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
										bind:value={editValue}
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
										bind:value={editAgentId}
										placeholder={$i18n.t('Leave empty for common connections')}
										autocomplete="off"
									/>
								</div>
							</div>

							<div class="flex items-center mb-2">
								<div class="text-xs text-gray-500 mr-2">{$i18n.t('Common Connection')}</div>
								<Tooltip
									content={editIsCommon
										? $i18n.t('This connection is available to all agents')
										: $i18n.t('This connection is specific to an agent')}
								>
									<Switch bind:state={editIsCommon} />
								</Tooltip>
							</div>
						</div>

						<div class="flex justify-end pt-3 text-sm font-medium gap-1.5">
							<button
								class="px-3.5 py-1.5 text-sm font-medium dark:bg-black dark:hover:bg-gray-900 dark:text-white bg-white text-black hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center"
								type="button"
								on:click={() => {
									const index = agentConnections.findIndex((c) => c === editConnection);
									if (index !== -1) {
										deleteConnection(index);
									}
									editConnection = null;
								}}
							>
								{$i18n.t('Delete')}
							</button>

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
{/if}
