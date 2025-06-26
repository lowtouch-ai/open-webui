<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import type { AgentConnection } from '$lib/apis/agent-connections';

  export let connections: AgentConnection[] = [];

  const dispatch = createEventDispatcher();

  const edit = (index: number) => {
    dispatch('edit', { index });
  };

  const del = (index: number) => {
    dispatch('delete', { index });
  };
</script>

<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
  <thead class="bg-gray-50 dark:bg-gray-800">
    <tr>
      <th class="px-4 py-3 text-left font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 text-xs">Name</th>
      <th class="px-4 py-3 text-left font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 text-xs">Value</th>
      <th class="px-4 py-3 text-left font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 text-xs">Scope</th>
      <th class="px-4 py-3 text-center font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 text-xs">Actions</th>
    </tr>
  </thead>
  <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
    {#if connections.length === 0}
      <tr>
        <td colspan="4" class="px-4 py-6 text-center text-gray-500 dark:text-gray-400">
          No agent connections
        </td>
      </tr>
    {:else}
      {#each connections as connection, i}
        <tr class="hover:bg-gray-50 dark:hover:bg-gray-900 transition">
          <td class="px-4 py-3 whitespace-nowrap">
            <div class="font-medium text-gray-900 dark:text-gray-100">{connection.key_name}</div>
          </td>
          <td class="px-4 py-3">
            <div class="text-sm text-gray-600 dark:text-gray-400 max-w-xs truncate">
              *** (hidden for security)
            </div>
          </td>
          <td class="px-4 py-3 whitespace-nowrap">
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {connection.is_common ? 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300' : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'}">
              {connection.is_common ? 'Common' : connection.agent_id || 'Specific'}
            </span>
          </td>
          <td class="px-4 py-3 whitespace-nowrap text-center">
            <div class="flex justify-center space-x-2">
              <button
                class="px-3 py-1 text-sm text-gray-600 dark:text-gray-300 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 rounded transition"
                on:click={() => edit(i)}
              >
                Edit
              </button>
              <button
                class="px-3 py-1 text-sm text-gray-600 dark:text-gray-300 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 rounded transition"
                on:click={() => del(i)}
              >
                Delete
              </button>
            </div>
          </td>
        </tr>
      {/each}
    {/if}
  </tbody>
</table>


