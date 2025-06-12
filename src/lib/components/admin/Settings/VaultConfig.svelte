<script lang="ts">
	import { onMount, createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';

	import { user as userStore } from '$lib/stores';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';

	// Get i18n from context
	const i18n: any = getContext('i18n');

	import {
		getVaultConfig,
		setVaultConfig,
		testVaultConnection,
		type VaultConfigForm
	} from '$lib/apis/vault';

	export let onSave = () => {};

	let loading = true;
	let saving = false;
	let testing = false;

	let vaultConfig: VaultConfigForm = {
		ENABLE_VAULT_INTEGRATION: false,
		VAULT_URL: '',
		VAULT_TOKEN: '',
		VAULT_MOUNT_PATH: '',
		VAULT_VERSION: 2,
		VAULT_TIMEOUT: 30,
		VAULT_VERIFY_SSL: true
	};

	const dispatch = createEventDispatcher();

	const fetchConfig = async () => {
		loading = true;

		try {
			const response = await getVaultConfig($userStore.token);
			vaultConfig = response;
		} catch (error) {
			console.error('Error fetching Vault config:', error);
			toast.error($i18n.t('Failed to fetch Vault configuration'));
		} finally {
			loading = false;
		}
	};

	const saveConfig = async () => {
		saving = true;

		try {
			await setVaultConfig($userStore.token, vaultConfig);
			toast.success($i18n.t('Vault configuration saved successfully'));
			dispatch('save');
			onSave();
		} catch (error) {
			console.error('Error saving Vault config:', error);
			toast.error($i18n.t('Failed to save Vault configuration'));
		} finally {
			saving = false;
		}
	};

	const testConnection = async () => {
		testing = true;

		try {
			const result = await testVaultConnection($userStore.token);
			if (result.success) {
				toast.success(result.message || $i18n.t('Vault connection successful'));
			} else {
				toast.error(result.message || $i18n.t('Vault connection failed'));
			}
		} catch (error) {
			console.error('Error testing Vault connection:', error);
			toast.error($i18n.t('Failed to test Vault connection'));
		} finally {
			testing = false;
		}
	};

	onMount(() => {
		fetchConfig();
	});
</script>

<div class="flex flex-col w-full">
	<div class="flex justify-between items-center mb-4">
		<div class="text-xl font-bold">{$i18n.t('HashiCorp Vault Integration')}</div>
	</div>

	{#if loading}
		<div class="flex justify-center items-center py-8">
			<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-white" />
		</div>
	{:else}
		<div class="grid grid-cols-1 gap-4">
			<div class="flex flex-col p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
				<div class="flex items-center mb-4">
					<div class="text-sm font-medium mr-2">{$i18n.t('Enable Vault Integration')}</div>
					<Tooltip
						content={vaultConfig.ENABLE_VAULT_INTEGRATION
							? $i18n.t('Agent connection secrets will be stored in HashiCorp Vault')
							: $i18n.t('Agent connection secrets will be stored in the local database')}
					>
						<Switch bind:state={vaultConfig.ENABLE_VAULT_INTEGRATION} />
					</Tooltip>
				</div>

				<div class="flex flex-col mb-4">
					<div class="mb-0.5 text-xs text-gray-500">{$i18n.t('Vault URL')}</div>
					<div class="flex-1">
						<input
							class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
							type="text"
							bind:value={vaultConfig.VAULT_URL}
							placeholder="https://vault.example.com:8200"
							autocomplete="off"
						/>
					</div>
				</div>

				<div class="flex flex-col mb-4">
					<div class="mb-0.5 text-xs text-gray-500">{$i18n.t('Vault Token')}</div>
					<div class="flex-1">
						<SensitiveInput
							className="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
							bind:value={vaultConfig.VAULT_TOKEN}
							placeholder="hvs.xxxxxxxxxxxxxxxxxxxxxxxx"
						/>
					</div>
				</div>

				<div class="flex flex-col mb-4">
					<div class="mb-0.5 text-xs text-gray-500">{$i18n.t('Vault Mount Path')}</div>
					<div class="flex-1">
						<input
							class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
							type="text"
							bind:value={vaultConfig.VAULT_MOUNT_PATH}
							placeholder="secret"
							autocomplete="off"
						/>
					</div>
				</div>

				<div class="flex flex-col mb-4">
					<div class="mb-0.5 text-xs text-gray-500">{$i18n.t('Vault KV Version')}</div>
					<div class="flex-1">
						<select
							class="w-full text-sm bg-transparent outline-hidden"
							bind:value={vaultConfig.VAULT_VERSION}
						>
							<option value={1}>KV Version 1</option>
							<option value={2}>KV Version 2</option>
						</select>
					</div>
				</div>

				<div class="flex flex-col mb-4">
					<div class="mb-0.5 text-xs text-gray-500">{$i18n.t('Vault Timeout (seconds)')}</div>
					<div class="flex-1">
						<input
							class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
							type="number"
							bind:value={vaultConfig.VAULT_TIMEOUT}
							min="1"
							max="300"
							autocomplete="off"
						/>
					</div>
				</div>

				<div class="flex items-center mb-4">
					<div class="text-sm font-medium mr-2">{$i18n.t('Verify SSL')}</div>
					<Tooltip
						content={vaultConfig.VAULT_VERIFY_SSL
							? $i18n.t('SSL certificates will be verified')
							: $i18n.t('SSL certificates will not be verified (not recommended for production)')}
					>
						<Switch bind:state={vaultConfig.VAULT_VERIFY_SSL} />
					</Tooltip>
				</div>

				<div class="flex justify-end gap-2">
					<button
						class="px-3.5 py-1.5 text-sm font-medium dark:bg-black dark:hover:bg-gray-900 dark:text-white bg-white text-black hover:bg-gray-100 transition rounded-full flex flex-row items-center"
						on:click={testConnection}
						disabled={testing || !vaultConfig.ENABLE_VAULT_INTEGRATION || !vaultConfig.VAULT_URL || !vaultConfig.VAULT_TOKEN}
					>
						{#if testing}
							<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white dark:border-black mr-2" />
						{/if}
						{$i18n.t('Test Connection')}
					</button>

					<button
						class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row items-center"
						on:click={saveConfig}
						disabled={saving}
					>
						{#if saving}
							<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white dark:border-black mr-2" />
						{/if}
						{$i18n.t('Save')}
					</button>
				</div>
			</div>
		</div>
	{/if}
</div>
