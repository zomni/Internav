import type { ApiEnvelope, LoginResponse } from '../types';

const BASE_URL = '/api/v1';
const TOKEN_STORAGE_KEY = 'internav.auth.tokens';

function loadStoredTokens(): { access: string | null; refresh: string | null } {
  try {
    const raw = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (!raw) return { access: null, refresh: null };
    const parsed = JSON.parse(raw) as { access_token?: string; refresh_token?: string };
    return { access: parsed.access_token ?? null, refresh: parsed.refresh_token ?? null };
  } catch {
    return { access: null, refresh: null };
  }
}

const stored = loadStoredTokens();
let accessToken: string | null = stored.access;
let refreshToken: string | null = stored.refresh;

export function setTokens(access: string, refresh: string) {
  accessToken = access;
  refreshToken = refresh;
  try {
    localStorage.setItem(
      TOKEN_STORAGE_KEY,
      JSON.stringify({ access_token: access, refresh_token: refresh }),
    );
  } catch {
    // ignore storage errors
  }
}

export function clearTokens() {
  accessToken = null;
  refreshToken = null;
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // ignore storage errors
  }
}

export function getAccessToken() {
  return accessToken;
}

async function refreshAccessToken(): Promise<boolean> {
  if (!refreshToken) return false;
  try {
    const res = await fetch(`${BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return false;
    const body = await res.json();
    const data = body.data as { access_token: string; refresh_token: string };
    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function apiRequest<T>(
  method: string,
  path: string,
  body?: unknown,
  opts?: { skipAuth?: boolean },
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (!opts?.skipAuth && accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }

  let res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401 && !opts?.skipAuth && refreshToken) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      headers['Authorization'] = `Bearer ${accessToken}`;
      res = await fetch(`${BASE_URL}${path}`, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
      });
    }
  }

  const json = (await res.json()) as ApiEnvelope<T>;
  if (!res.ok || !json.success) {
    throw new ApiError(res.status, json.message || json.errors?.[0] || 'Request failed');
  }
  return json.data;
}

export const api = {
  get: <T>(path: string) => apiRequest<T>('GET', path),
  post: <T>(path: string, body?: unknown) => apiRequest<T>('POST', path, body),
  put: <T>(path: string, body?: unknown) => apiRequest<T>('PUT', path, body),
  patch: <T>(path: string, body?: unknown) => apiRequest<T>('PATCH', path, body),
  delete: <T>(path: string) => apiRequest<T>('DELETE', path),
  upload: async <T>(path: string, formData: FormData): Promise<T> => {
    const headers: Record<string, string> = {};
    if (accessToken) headers['Authorization'] = `Bearer ${accessToken}`;
    let res = await fetch(`${BASE_URL}${path}`, { method: 'POST', headers, body: formData });
    if (res.status === 401 && refreshToken) {
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        headers['Authorization'] = `Bearer ${accessToken}`;
        res = await fetch(`${BASE_URL}${path}`, { method: 'POST', headers, body: formData });
      }
    }
    const json = (await res.json()) as ApiEnvelope<T>;
    if (!res.ok || !json.success) throw new ApiError(res.status, json.message || 'Upload failed');
    return json.data;
  },
  login: async (email: string, password: string) => {
    const res = await fetch(`${BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const json = (await res.json()) as ApiEnvelope<LoginResponse>;
    if (!res.ok || !json.success) throw new ApiError(res.status, json.message || 'Login failed');
    return json.data;
  },
};
