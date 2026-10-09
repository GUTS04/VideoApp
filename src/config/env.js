const apiBase = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8001';

export const API_BASE_URL = apiBase.replace(/\/$/, '');

export function getWebSocketUrl(accessToken) {
  const wsBase = import.meta.env.VITE_WS_URL ?? API_BASE_URL.replace(/^http/, 'ws');
  const base = wsBase.replace(/\/$/, '');
  return `${base}/ws/connect?token=${encodeURIComponent(accessToken)}`;
}
