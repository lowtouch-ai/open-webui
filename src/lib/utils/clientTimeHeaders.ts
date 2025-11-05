export const getClientTimeHeaders = (): Record<string, string> => {
  const now = new Date();
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';

  const offsetMinutes = -now.getTimezoneOffset();
  const sign = offsetMinutes >= 0 ? '+' : '-';
  const abs = Math.abs(offsetMinutes);
  const hh = Math.floor(abs / 60).toString().padStart(2, '0');
  const mm = (abs % 60).toString().padStart(2, '0');
  const offsetStr = `${sign}${hh}:${mm}`;

  return {
    'X-Client-Local-Time': now.toISOString(),
    'X-Client-Timezone': tz,
    'X-Client-UTC-Offset': offsetStr
  };
};

export const mergeHeaders = (existing: HeadersInit | undefined, extra: Record<string, string>): HeadersInit => {
  const headers = new Headers(existing || {});
  for (const [k, v] of Object.entries(extra)) headers.set(k, v);
  return headers;
};