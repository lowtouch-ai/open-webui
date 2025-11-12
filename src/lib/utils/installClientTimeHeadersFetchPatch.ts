import {
  WEBUI_BASE_URL,
  WEBUI_API_BASE_URL,
  OPENAI_API_BASE_URL,
  OLLAMA_API_BASE_URL,
  AUDIO_API_BASE_URL,
  IMAGES_API_BASE_URL,
  RETRIEVAL_API_BASE_URL
} from '$lib/constants';
import { getClientTimeHeaders, mergeHeaders } from './clientTimeHeaders';

export const installClientTimeHeadersFetchPatch = (): void => {
  if (typeof window === 'undefined') return;
  // Avoid double-patching
  if ((window as any).__clientTimeHeadersPatched) return;
  (window as any).__clientTimeHeadersPatched = true;

  const basePrefixes = [
    WEBUI_BASE_URL,
    WEBUI_API_BASE_URL,
    OPENAI_API_BASE_URL,
    OLLAMA_API_BASE_URL,
    AUDIO_API_BASE_URL,
    IMAGES_API_BASE_URL,
    RETRIEVAL_API_BASE_URL
  ]
    .filter((p) => !!p) as string[];

  const originalFetch = window.fetch.bind(window);

  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    try {
      const urlStr = typeof input === 'string'
        ? input
        : (input instanceof URL)
        ? input.href
        : (input as Request).url;

      const shouldAttach = basePrefixes.some((prefix) => urlStr?.startsWith(prefix)) ||
        (typeof urlStr === 'string' && (urlStr.startsWith('/api') || urlStr.startsWith('/openai') || urlStr.startsWith('/ollama')));

      if (shouldAttach) {
        const extra = getClientTimeHeaders();
        const newInit: RequestInit = { ...(init || {}) };
        newInit.headers = mergeHeaders(init?.headers, extra);
        try {
          // Log in dev to help verify headers
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const isDev = (typeof import.meta !== 'undefined' && (import.meta as any).env?.DEV) || false;
          if (isDev) {
            console.debug('[client-time-headers] attached', extra, urlStr);
          }
        } catch (_) {}
        return originalFetch(input as any, newInit);
      }
    } catch (e) {
      // If anything goes wrong, fall back to original fetch
    }

    return originalFetch(input as any, init);
  };
};