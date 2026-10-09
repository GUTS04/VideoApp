import { apiRequestAuthWithRefresh } from './client';

export function blockUser(accessToken, blockedUserId) {
  return apiRequestAuthWithRefresh(`/api/v1/blocks/${blockedUserId}`, accessToken, {
    method: 'POST',
  });
}

export function reportUser(accessToken, payload) {
  return apiRequestAuthWithRefresh('/api/v1/reports', accessToken, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
