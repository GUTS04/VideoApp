import { apiRequestAuthWithRefresh } from './client';

export function fetchCoinBalance(accessToken) {
  return apiRequestAuthWithRefresh('/api/v1/coins/balance', accessToken);
}

export function fetchCoinTransactions(accessToken, { skip = 0, limit = 20 } = {}) {
  return apiRequestAuthWithRefresh(
    `/api/v1/coins/transactions?skip=${skip}&limit=${limit}`,
    accessToken,
  );
}
