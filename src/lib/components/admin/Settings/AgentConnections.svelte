<script lang="ts">
	import { onMount, createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { user as userStore } from '$lib/stores';

	const dispatch = createEventDispatcher();

	import {
		listAllAgentConnections,
		type AgentConnection
	} from '$lib/apis/agent-connections';

	export let onSave = () => {};

	let loading = true;
	let connections: AgentConnection[] = [];

	// Summary data
	$: userSummary = connections.reduce((acc, conn) => {
		const userId = conn.user_id || 'unknown';
		const userName = conn.user_name || conn.user_email || 'Unknown User';
		
		if (!acc[userId]) {
			acc[userId] = {
				name: userName,
				count: 0,
				commonCount: 0,
				specificCount: 0
			};
		}
		
		acc[userId].count++;
		if (conn.is_common) {
			acc[userId].commonCount++;
		} else {
			acc[userId].specificCount++;
		}
		
		return acc;
	}, {});

	$: totalUsers = Object.keys(userSummary).length;
	$: totalConnections = connections.length;

	const fetchConnections = async () => {
		loading = true;
		try {
			connections = await listAllAgentConnections($userStore.token);
		} catch (error) {
			console.error('Error fetching agent connections:', error);
			toast.error($i18n.t('Failed to fetch agent connections'));
		} finally {
			loading = false;
		}
	};

	onMount(() => {
		fetchConnections();
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		// No form submission needed for this view
	}}
>
	<div class="mt-0.5 space-y-3 overflow-y-scroll scrollbar-hidden h-full">
		<div class="">
			<div class="mb-3.5">
				<div class=" mb-2.5 text-base font-medium">{$i18n.t('Agent Connections Overview')}</div>

				<hr class=" border-gray-100 dark:border-gray-850 my-2" />

				{#if loading}
					<div class="flex justify-center items-center py-8">
						<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-white" />
					</div>
				{:else}
					<!-- Summary Stats -->
					<div class="mb-2.5">
						<div class=" mb-1 text-xs font-medium">{$i18n.t('Summary')}</div>
						<div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
							<div class="bg-gray-50 dark:bg-gray-850 rounded-lg p-3">
								<div class="text-lg font-bold text-gray-700 dark:text-gray-300">{totalConnections}</div>
								<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Total Connections')}</div>
							</div>
							<div class="bg-gray-50 dark:bg-gray-850 rounded-lg p-3">
								<div class="text-lg font-bold text-gray-700 dark:text-gray-300">{totalUsers}</div>
								<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Active Users')}</div>
							</div>
							<div class="bg-gray-50 dark:bg-gray-850 rounded-lg p-3">
								<div class="text-lg font-bold text-gray-700 dark:text-gray-300">
									{connections.filter(c => c.is_common).length}
								</div>
								<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Common Connections')}</div>
							</div>
						</div>
					</div>

					{#if totalConnections === 0}
						<div class="flex flex-col items-center justify-center py-8 text-gray-500">
							<div class="text-sm font-medium mb-2">{$i18n.t('No agent connections')}</div>
							<div class="text-xs">{$i18n.t('Users can create connections through their settings')}</div>
						</div>
					{:else}
						<!-- User Summary Table -->
						<div class="mb-2.5">
							<div class=" mb-1 text-xs font-medium">{$i18n.t('Connections by User')}</div>
							<div class="bg-gray-50 dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700">
								<div class="overflow-x-auto">
									<table class="min-w-full text-xs">
										<thead class="bg-gray-100 dark:bg-gray-800">
											<tr>
												<th class="px-3 py-2 text-left font-medium text-gray-700 dark:text-gray-300">
													{$i18n.t('User')}
												</th>
												<th class="px-3 py-2 text-center font-medium text-gray-700 dark:text-gray-300">
													{$i18n.t('Total')}
												</th>
												<th class="px-3 py-2 text-center font-medium text-gray-700 dark:text-gray-300">
													{$i18n.t('Personal')}
												</th>
												<th class="px-3 py-2 text-center font-medium text-gray-700 dark:text-gray-300">
													{$i18n.t('Common')}
												</th>
											</tr>
										</thead>
										<tbody class="bg-gray-50 dark:bg-gray-850 divide-y divide-gray-200 dark:border-gray-700">
											{#each Object.entries(userSummary) as [userId, summary]}
												<tr>
													<td class="px-3 py-2">
														<div class="text-xs text-gray-900 dark:text-gray-100">
															{summary.name}
														</div>
													</td>
													<td class="px-3 py-2 text-center">
														<span class="text-xs text-gray-700 dark:text-gray-300">
															{summary.count}
														</span>
													</td>
													<td class="px-3 py-2 text-center">
														<span class="text-xs text-gray-700 dark:text-gray-300">
															{summary.specificCount}
														</span>
													</td>
													<td class="px-3 py-2 text-center">
														<span class="text-xs text-gray-700 dark:text-gray-300">
															{summary.commonCount}
														</span>
													</td>
												</tr>
											{/each}
										</tbody>
									</table>
								</div>
							</div>
						</div>

						<!-- Refresh Button -->
						<div class="flex justify-end">
							<button
								class="px-3 py-1.5 text-xs bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300 transition rounded-lg font-medium"
								type="button"
								on:click={fetchConnections}
								disabled={loading}
							>
								{loading ? $i18n.t('Refreshing...') : $i18n.t('Refresh')}
							</button>
						</div>
					{/if}
				{/if}
			</div>
		</div>
	</div>
</form>
