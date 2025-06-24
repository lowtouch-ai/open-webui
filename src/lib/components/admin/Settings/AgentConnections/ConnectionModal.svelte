<script lang="ts">
import { createEventDispatcher, onMount } from 'svelte';
import { getContext } from 'svelte';
import { toast } from 'svelte-sonner';

import Modal from '$lib/components/common/Modal.svelte';
import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
import Switch from '$lib/components/common/Switch.svelte';
import Tooltip from '$lib/components/common/Tooltip.svelte';

import type { AgentConnection } from '$lib/apis/agent-connections';

const i18n: any = getContext('i18n');

export let show: boolean = false; // bindable
export let mode: 'add' | 'edit' = 'add';
export let connection: AgentConnection | null = null; // only for edit

const dispatch = createEventDispatcher();

let name = '';
let value = '';
let agent_id = '';
let is_common = false;

onMount(() => {
  if (mode === 'edit' && connection) {
    ({ name, value } = connection);
    agent_id = connection.agent_id || '';
    is_common = connection.is_common || false;
  }
});

$: if (mode === 'edit' && connection) {
  name = connection.name;
  value = connection.value;
  agent_id = connection.agent_id || '';
  is_common = connection.is_common || false;
}

// Validate connection name (alphanumeric, no spaces)
const validateConnectionName = (n: string) => /^[a-zA-Z0-9_]+$/.test(n);

function close() {
  dispatch('close');
  show = false;
}

function handleSubmit(e: Event) {
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
  const conn: AgentConnection = {
    name,
    value,
    agent_id: agent_id || null,
    is_common
  } as AgentConnection;
  dispatch('save', { connection: conn });
  close();
}

function handleDelete() {
  dispatch('delete');
  close();
}
</script>

<Modal size="sm" bind:show>
  <div>
    <div class="flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
      <div class="text-lg font-medium self-center font-primary">
        {mode === 'add' ? $i18n.t('Add Agent Connection') : $i18n.t('Edit Agent Connection')}
      </div>
      <button class="self-center" on:click={close}>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
          <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
        </svg>
      </button>
    </div>

    <div class="flex flex-col md:flex-row w-full px-4 pb-4 md:space-x-4 dark:text-gray-200">
      <div class="flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
        <form class="flex flex-col w-full" on:submit={handleSubmit}>
          <div class="px-1">
            <div class="flex flex-col w-full mb-2">
              <div class="mb-0.5 text-xs text-gray-500">{$i18n.t('Name')}</div>
              <div class="flex-1">
                <input class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden" type="text" bind:value={name} placeholder={$i18n.t('Connection Name')} autocomplete="off" required />
              </div>
            </div>
            <div class="flex flex-col w-full mb-2">
              <div class="mb-0.5 text-xs text-gray-500">{$i18n.t('Value')}</div>
              <div class="flex-1">
                <SensitiveInput
                  inputClassName="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
                  bind:value={value}
                  placeholder={$i18n.t('Connection Value')}
                  required
                />
              </div>
            </div>
            <div class="flex flex-col w-full mb-2">
              <div class="mb-0.5 text-xs text-gray-500">{$i18n.t('Agent ID (Optional)')}</div>
              <div class="flex-1">
                <input class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden" type="text" bind:value={agent_id} placeholder={$i18n.t('Leave empty for common connections')} autocomplete="off" />
              </div>
            </div>
            <div class="flex items-center mb-2">
              <div class="text-xs text-gray-500 mr-2">{$i18n.t('Common Connection')}</div>
              <Tooltip content={is_common ? $i18n.t('This connection is available to all agents') : $i18n.t('This connection is specific to an agent')}>
                <Switch bind:state={is_common} />
              </Tooltip>
            </div>
          </div>
          <div class="flex justify-end pt-3 text-sm font-medium gap-1.5">
            {#if mode === 'edit'}
            <button type="button" class="px-3.5 py-1.5 text-sm font-medium dark:bg-black dark:hover:bg-gray-900 dark:text-white bg-white text-black hover:bg-gray-100 transition rounded-full" on:click={handleDelete}>{$i18n.t('Delete')}</button>
            {/if}
            <button type="submit" class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full">{$i18n.t('Save')}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</Modal>
