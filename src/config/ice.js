import { API_BASE_URL } from './env';

const DEFAULT_ICE = [{ urls: 'stun:stun.l.google.com:19302' }];

let cachedIceServers = null;

export async function getIceServers() {
  if (cachedIceServers) {
    return cachedIceServers;
  }

  if (import.meta.env.VITE_ICE_SERVERS) {
    try {
      cachedIceServers = JSON.parse(import.meta.env.VITE_ICE_SERVERS);
      return cachedIceServers;
    } catch {
      console.warn('Invalid VITE_ICE_SERVERS JSON, using API/default');
    }
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/config/ice`);
    if (response.ok) {
      const data = await response.json();
      cachedIceServers = data.iceServers ?? DEFAULT_ICE;
      return cachedIceServers;
    }
  } catch {
    /* fall through */
  }

  cachedIceServers = DEFAULT_ICE;
  return cachedIceServers;
}
