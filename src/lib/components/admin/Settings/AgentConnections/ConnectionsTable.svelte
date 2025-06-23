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
      <th class="px-4 py-2 text-left font-semibold">Name</th>
      <th class="px-4 py-2 text-left font-semibold">Scope</th>
      <th class="px-4 py-2 text-center font-semibold">Actions</th>
    </tr>
  </thead>
  <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
    {#if connections.length === 0}
      <tr>
        <td colspan="3" class="px-4 py-6 text-center text-gray-500 dark:text-gray-400">
          No agent connections
        </td>
      </tr>
    {:else}
      {#each connections as connection, i}
        <tr class="hover:bg-gray-50 dark:hover:bg-gray-900 transition">
          <td class="px-4 py-2 whitespace-nowrap font-medium">{connection.name}</td>
          <td class="px-4 py-2 whitespace-nowrap">
            {connection.is_common ? 'Common' : connection.agent_id || '—'}
          </td>
          <td class="px-4 py-2 whitespace-nowrap text-center space-x-2">
            <button
              class="px-2 py-0.5 bg-transparent hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
              on:click={() => edit(i)}
            >
              Edit
            </button>
            <button
              class="px-2 py-0.5 bg-transparent hover:bg-red-100 text-red-600 dark:hover:bg-red-900 rounded"
              on:click={() => del(i)}
            >
              Delete
            </button>
          </td>
        </tr>
      {/each}
    {/if}
  </tbody>
</table>

<style>
  th {
    @apply uppercase text-xs tracking-wide text-gray-500 dark:text-gray-400;
  }
</style>
