<script lang="ts">
import { createEventDispatcher, onMount } from 'svelte';
import { getContext } from 'svelte';
import { toast } from 'svelte-sonner';

import Modal from '$lib/components/common/Modal.svelte';
import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
import Switch from '$lib/components/common/Switch.svelte';
import Tooltip from '$lib/components/common/Tooltip.svelte';
import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

import { models, user } from '$lib/stores';
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
let initialized = false;
let saving = false;
let showDeleteConfirmDialog = false;

// Reset agent_id when common connection is enabled
$: if (is_common) {
  agent_id = '';
}

// Filter models to get unique agent IDs; ensure current connection's agent_id is included on edit
$: availableAgentIds = [
  ...new Set([
    ...$models
      .map(model => {
        // Use the same logic as extractAgentIdFromModel
        const info = model.info as Record<string, unknown> | undefined;
        const meta = model.meta as Record<string, unknown> | undefined;
        
        const agentId = 
          (info?.meta as Record<string, unknown>)?.agent_id || 
          meta?.agent_id || 
          model.agent_id;

        if (typeof agentId === 'string') return agentId;

        // Fallback: try to extract from model ID if it follows a pattern
        // e.g., agent:gpt-4 -> agent ID would be "agent"
        if (typeof model.id === 'string' && model.id.includes(':')) {
          const parts = model.id.split(':');
          if (parts.length >= 2) {
            return parts[0];
          }
        }

        return null;
      })
      .filter(id => id && id.length > 0),
    ...(mode === 'edit' && connection?.agent_id ? [connection.agent_id] : [])
  ])
].sort();

// Initialize form values when connection changes (only once per connection)
$: if (mode === 'edit' && connection && !initialized) {
  name = connection.key_name;
  value = ''; // Don't pre-fill sensitive values for security
  agent_id = connection.agent_id || '';
  is_common = connection.is_common || false;
  initialized = true;
}

// Reset initialization flag when mode changes or connection changes
$: if (mode === 'add' || !connection) {
  initialized = false;
  if (mode === 'add') {
    name = '';
    value = '';
    agent_id = '';
    is_common = false;
  }
}

// No strict validation on name; allow arbitrary characters. Only require non-empty.
function validateConnectionName(n: string) {
  return n.length > 0;
}

function close() {
  // Reset form and state when closing
  name = '';
  value = '';
  agent_id = '';
  is_common = false;
  initialized = false;
  dispatch('close');
  show = false;
}

async function handleSubmit(e: Event) {
  e.preventDefault();
  if (saving) return;
  
  if (!name) {
    toast.error($i18n.t('Name is required'));
    return;
  }
  if (mode === 'add' && !value) {
    toast.error($i18n.t('Value is required'));
    return;
  }
  
  saving = true;
  try {
    const conn = {
      key_name: name,
      key_value: value,
      agent_id: is_common ? null : (agent_id || null),
      is_common
    };
    dispatch('save', { connection: conn });
    close();
  } finally {
    saving = false;
  }
}

function handleDelete() {
  showDeleteConfirmDialog = true;
}

function confirmDelete() {
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
            <div class="flex flex-col w-full mb-3">
              <div class="mb-1 text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Name')}</div>
              <div class="flex-1">
                <input 
                  class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
                  type="text" 
                  bind:value={name} 
                  placeholder={$i18n.t('Enter connection name (any characters allowed)')} 
                  autocomplete="off" 
                  data-cy="connection-name"
                  required 
                />
              </div>
              <div class="mt-1 text-xs text-gray-500">{$i18n.t('Any characters allowed, e.g., "car/hummer"')}</div>
            </div>
            <div class="flex flex-col w-full mb-3">
              <div class="mb-1 text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Value')}</div>
              <div class="flex-1">
                <SensitiveInput
                  inputClassName="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  bind:value={value}
                  placeholder={mode === 'edit' ? $i18n.t('Enter new value or leave empty to keep current') : $i18n.t('Enter connection value (API key, token, etc.)')}
                  data-cy="connection-value"
                  required={mode === 'add'}
                />
              </div>
              <div class="mt-1 text-xs text-gray-500">
                {mode === 'edit' ? $i18n.t('Leave empty to keep the current value unchanged') : $i18n.t('The secret value for this connection')}
              </div>
            </div>

            <div class="flex items-center justify-between mb-4 p-3 bg-gray-50 dark:bg-gray-850 border border-gray-200 dark:border-gray-700 rounded-md">
              <div class="flex flex-col">
                <div class="text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Common Connection')}</div>
                <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {is_common ? $i18n.t('This connection will be available to all agents') : $i18n.t('This connection can be assigned to a specific agent')}
                </div>
              </div>
              <div class="flex items-center">
                <Switch bind:state={is_common} data-cy="connection-is-common" />
              </div>
            </div>

            {#if !is_common}
              <div class="flex flex-col w-full mb-3">
                <div class="mb-1 text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Agent ID')} <span class="text-gray-500 font-normal">({$i18n.t('Optional')})</span></div>
                <div class="flex-1">
                  <select 
                    class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
                    bind:value={agent_id}
                    data-cy="connection-agent-id"
                  >
                    <option value="">{$i18n.t('Select agent or leave empty for all')}</option>
                    {#each availableAgentIds as agentId}
                      <option value={agentId} class="bg-white dark:bg-gray-800">{agentId}</option>
                    {/each}
                  </select>
                </div>
                <div class="mt-1 text-xs text-gray-500">{$i18n.t('Select a specific agent or leave empty to make this connection available to all agents')}</div>
              </div>
            {/if}

          </div>
          <div class="flex justify-end pt-4 text-sm font-medium gap-3 border-t border-gray-200 dark:border-gray-700 mt-6">
            {#if mode === 'edit'}
              <button 
                type="button" 
                class="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-750 hover:text-gray-700 dark:hover:text-gray-200 transition rounded-md" 
                on:click={handleDelete}
              >
                {$i18n.t('Delete')}
              </button>
            {/if}
            <button 
              type="submit" 
              disabled={saving}
              data-cy={mode === 'add' ? 'create-connection-button' : 'update-connection-button'}
              class="px-4 py-2 text-sm font-medium bg-black hover:bg-gray-900 disabled:bg-gray-500 disabled:cursor-not-allowed text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 dark:disabled:bg-gray-600 dark:disabled:text-gray-300 transition rounded-lg flex items-center gap-2"
            >
              {#if saving}
                <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {$i18n.t('Saving...')}
              {:else}
                {mode === 'add' ? $i18n.t('Create Connection') : $i18n.t('Update Connection')}
              {/if}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</Modal>

<!-- Delete Confirmation Dialog -->
<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	on:confirm={confirmDelete}
>
	<div class="text-sm dark:text-gray-300">
		{$i18n.t('Are you sure you want to delete this agent connection? This action cannot be undone.')}
	</div>
</ConfirmDialog> 