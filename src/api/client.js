import { API_BASE_URL } from '../config/env';
import { refreshTokens } from './auth';
import {
  clearAuth,
  getAccessToken,
  getRefreshToken,
  updateAccessToken,
} from '../utils/authStorage';

let refreshPromise = null;

async function parseResponse(response) {
  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }
  return data;
}

function errorFromResponse(response, data) {
  const message =
    data?.detail ??
    (typeof data?.message === 'string' ? data.message : null) ??
    `Request failed (${response.status})`;
  return new Error(Array.isArray(message) ? message[0]?.msg ?? 'Request failed' : message);
}

async function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        throw new Error('No refresh token');
      }
      const tokens = await refreshTokens(refreshToken);
      updateAccessToken(tokens.access_token);
      if (tokens.refresh_token) {
        localStorage.setItem('videoapp_refresh_token', tokens.refresh_token);
      }
      return tokens.access_token;
    })().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

export async function apiRequest(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers ?? {}),
  };

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  const data = await parseResponse(response);
  if (!response.ok) {
    throw errorFromResponse(response, data);
  }
  return data;
}

export async function apiRequestAuth(path, accessToken, options = {}) {
  return apiRequest(path, {
    ...options,
    headers: {
      Authorization: `Bearer ${accessToken}`,
      ...(options.headers ?? {}),
    },
  });
}

export async function apiRequestAuthWithRefresh(path, accessToken, options = {}) {
  let token = accessToken || getAccessToken();
  if (!token) {
    throw new Error('Not authenticated');
  }

  let response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...(options.headers ?? {}),
    },
  });

  if (response.status === 401) {
    try {
      token = await refreshAccessToken();
      response = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
          ...(options.headers ?? {}),
        },
      });
    } catch {
      clearAuth();
      throw new Error('Session expired. Please sign in again.');
    }
  }

  const data = await parseResponse(response);
  if (!response.ok) {
    if (response.status === 401) {
      clearAuth();
    }
    throw errorFromResponse(response, data);
  }
  return data;
}
