<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	
	const dispatch = createEventDispatcher();
	
	export let src: string;
	export let title: string = '';
	export let className: string = '';
	
	let audioElement: HTMLAudioElement;
	let isPlaying = false;
	let currentTime = 0;
	let duration = 0;
	let isLoading = false;
	let hasError = false;
	
	const formatTime = (time: number): string => {
		const minutes = Math.floor(time / 60);
		const seconds = Math.floor(time % 60);
		return `${minutes}:${seconds.toString().padStart(2, '0')}`;
	};
	
	const togglePlay = async () => {
		if (!audioElement) return;
		
		try {
			if (isPlaying) {
				audioElement.pause();
			} else {
				isLoading = true;
				await audioElement.play();
				isLoading = false;
			}
		} catch (error) {
			console.error('Error playing audio:', error);
			toast.error('Failed to play audio');
			isLoading = false;
			hasError = true;
		}
	};
	
	const handleTimeUpdate = () => {
		if (audioElement) {
			currentTime = audioElement.currentTime;
		}
	};
	
	const handleLoadedMetadata = () => {
		if (audioElement) {
			duration = audioElement.duration;
		}
	};
	
	const handlePlay = () => {
		isPlaying = true;
		isLoading = false;
	};
	
	const handlePause = () => {
		isPlaying = false;
	};
	
	const handleEnded = () => {
		isPlaying = false;
		currentTime = 0;
	};
	
	const handleError = (event) => {
		console.error('Audio error:', event);
		console.error('Audio src:', src);
		hasError = true;
		isLoading = false;
		isPlaying = false;
		
		// Try to provide more specific error information
		if (audioElement && audioElement.error) {
			const errorCode = audioElement.error.code;
			const errorMessages = {
				1: 'MEDIA_ERR_ABORTED - The user aborted the audio',
				2: 'MEDIA_ERR_NETWORK - A network error occurred',
				3: 'MEDIA_ERR_DECODE - An error occurred while decoding the audio',
				4: 'MEDIA_ERR_SRC_NOT_SUPPORTED - The audio format is not supported'
			};
			console.error('Audio error code:', errorCode, errorMessages[errorCode] || 'Unknown error');
		}
		
		toast.error('Failed to load audio - this may be due to CORS restrictions or unsupported format');
	};
	
	const handleSeek = (event: Event) => {
		const target = event.target as HTMLInputElement;
		const seekTime = (parseFloat(target.value) / 100) * duration;
		if (audioElement) {
			audioElement.currentTime = seekTime;
		}
	};
</script>

<div class="audio-player {className} bg-gray-50 dark:bg-gray-800 rounded-lg p-3 my-2 max-w-sm">
	<audio
		bind:this={audioElement}
		{src}
		preload="metadata"
		on:timeupdate={handleTimeUpdate}
		on:loadedmetadata={handleLoadedMetadata}
		on:play={handlePlay}
		on:pause={handlePause}
		on:ended={handleEnded}
		on:error={handleError}
	>
		<track kind="captions" />
	</audio>
	
	<div class="flex items-center space-x-3">
		<!-- Play/Pause Button -->
		<button
			class="flex-shrink-0 w-10 h-10 bg-blue-500 hover:bg-blue-600 text-white rounded-full flex items-center justify-center transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
			on:click={togglePlay}
			disabled={hasError || isLoading}
			aria-label={isPlaying ? 'Pause' : 'Play'}
		>
			{#if isLoading}
				<svg class="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
			{:else if hasError}
				<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
					<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
				</svg>
			{:else if isPlaying}
				<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
					<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
				</svg>
			{:else}
				<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
					<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
				</svg>
			{/if}
		</button>
		
		<!-- Progress and Time -->
		<div class="flex-1 min-w-0">
			{#if title}
				<div class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate mb-1">
					{title}
				</div>
			{/if}
			
			<!-- Progress Bar -->
			<div class="flex items-center space-x-2">
				<span class="text-xs text-gray-500 dark:text-gray-400 tabular-nums">
					{formatTime(currentTime)}
				</span>
				
				<div class="flex-1">
					<input
						type="range"
						min="0"
						max="100"
						value={duration > 0 ? (currentTime / duration) * 100 : 0}
						on:input={handleSeek}
						class="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
						disabled={hasError || duration === 0}
					/>
				</div>
				
				<span class="text-xs text-gray-500 dark:text-gray-400 tabular-nums">
					{duration > 0 ? formatTime(duration) : '--:--'}
				</span>
			</div>
		</div>
	</div>
	
	{#if hasError}
		<div class="mt-2 text-xs text-red-500 dark:text-red-400">
			Failed to load audio. <a href={src} target="_blank" rel="nofollow" class="underline">Open link</a>
		</div>
	{/if}
</div>

<style>
	.slider::-webkit-slider-thumb {
		appearance: none;
		height: 16px;
		width: 16px;
		border-radius: 50%;
		background: #3b82f6;
		cursor: pointer;
		border: 2px solid #ffffff;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
	}
	
	.slider::-moz-range-thumb {
		height: 16px;
		width: 16px;
		border-radius: 50%;
		background: #3b82f6;
		cursor: pointer;
		border: 2px solid #ffffff;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
	}
	
	.slider::-webkit-slider-track {
		height: 8px;
		border-radius: 4px;
		background: linear-gradient(to right, #3b82f6 0%, #3b82f6 var(--progress, 0%), #e5e7eb var(--progress, 0%), #e5e7eb 100%);
	}
	
	.slider::-moz-range-track {
		height: 8px;
		border-radius: 4px;
		background: #e5e7eb;
	}
	
	.slider::-moz-range-progress {
		height: 8px;
		border-radius: 4px;
		background: #3b82f6;
	}
</style>