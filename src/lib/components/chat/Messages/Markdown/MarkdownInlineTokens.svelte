<script lang="ts">
	import DOMPurify from 'dompurify';
	import { toast } from 'svelte-sonner';

	import type { Token } from 'marked';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	import { WEBUI_BASE_URL } from '$lib/constants';
	import { copyToClipboard, unescapeHtml } from '$lib/utils';

	import Image from '$lib/components/common/Image.svelte';
	import KatexRenderer from './KatexRenderer.svelte';
	import Source from './Source.svelte';
	import AudioPlayer from './AudioPlayer.svelte';
	import HtmlToken from './HTMLToken.svelte';
	import TextToken from './MarkdownInlineTokens/TextToken.svelte';
	import CodespanToken from './MarkdownInlineTokens/CodespanToken.svelte';
	import MentionToken from './MarkdownInlineTokens/MentionToken.svelte';

	export let id: string;
	export let done = true;
	export let tokens: Token[];
	export let onSourceClick: Function = () => {};
	
	// Function to check if a URL is an audio file
	const isAudioUrl = (url: string): boolean => {
		const audioExtensions = ['.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac', '.wma'];
		const urlLower = url.toLowerCase();
		const isAudio = audioExtensions.some(ext => urlLower.includes(ext)) || urlLower.includes('/audio/');
		
		// Debug logging
		console.log('Checking URL for audio:', url);
		console.log('URL lowercase:', urlLower);
		console.log('Is audio URL:', isAudio);
		
		return isAudio;
	};
	
	// Function to extract filename from URL for audio title
	const getAudioTitle = (url: string): string => {
		try {
			const urlObj = new URL(url);
			const pathname = urlObj.pathname;
			const filename = pathname.split('/').pop() || '';
			return filename.replace(/\.[^/.]+$/, ''); // Remove extension
		} catch {
			return 'Audio';
		}
	};
</script>

{#each tokens as token}
	{#if token.type === 'escape'}
		{unescapeHtml(token.text)}
	{:else if token.type === 'html'}
		<HtmlToken {id} {token} {onSourceClick} />
	{:else if token.type === 'link'}
		{#if isAudioUrl(token.href)}
			<AudioPlayer 
				src={token.href} 
				title={getAudioTitle(token.href)}
				className="inline-block"
			/>
		{:else if token.tokens}
			<a href={token.href} target="_blank" rel="nofollow" title={token.title}>
				<svelte:self id={`${id}-a`} tokens={token.tokens} {onSourceClick} {done} />
			</a>
		{:else}
			<a href={token.href} target="_blank" rel="nofollow" title={token.title}>{token.text}</a>
		{/if}
	{:else if token.type === 'image'}
		<Image src={token.href} alt={token.text} />
	{:else if token.type === 'strong'}
		<strong><svelte:self id={`${id}-strong`} tokens={token.tokens} {onSourceClick} /></strong>
	{:else if token.type === 'em'}
		<em><svelte:self id={`${id}-em`} tokens={token.tokens} {onSourceClick} /></em>
	{:else if token.type === 'codespan'}
		{#if isAudioUrl(unescapeHtml(token.text))}
			<AudioPlayer 
				src={unescapeHtml(token.text)} 
				title={getAudioTitle(unescapeHtml(token.text))}
				className="inline-block"
			/>
		{:else}
			<!-- svelte-ignore a11y-click-events-have-key-events -->
			<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
			<code
				class="codespan cursor-pointer"
				on:click={() => {
					copyToClipboard(unescapeHtml(token.text));
					toast.success($i18n.t('Copied to clipboard'));
				}}>{unescapeHtml(token.text)}</code
			>
		{/if}
	{:else if token.type === 'br'}
		<br />
	{:else if token.type === 'del'}
		<del><svelte:self id={`${id}-del`} tokens={token.tokens} {onSourceClick} /></del>
	{:else if token.type === 'inlineKatex'}
		{#if token.text}
			<KatexRenderer content={token.text} displayMode={false} />
		{/if}
	{:else if token.type === 'iframe'}
		<iframe
			src="{WEBUI_BASE_URL}/api/v1/files/{token.fileId}/content"
			title={token.fileId}
			width="100%"
			frameborder="0"
			onload="this.style.height=(this.contentWindow.document.body.scrollHeight+20)+'px';"
		></iframe>
	{:else if token.type === 'mention'}
		<MentionToken {token} />
	{:else if token.type === 'text'}
		<TextToken {token} {done} />
	{/if}
{/each}
