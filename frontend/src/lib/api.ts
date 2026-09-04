import type { AuthResponse, DashboardResponse, UserProfileResponse } from '@/types/api';
import { sessionToken } from '@/lib/session';

const configuredApiUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '');
const isLocalHost = ['localhost', '127.0.0.1'].includes(window.location.hostname);
const API_BASE_URL = configuredApiUrl && (!configuredApiUrl.startsWith('http://localhost') && !configuredApiUrl.startsWith('http://127.0.0.1') || isLocalHost)
  ? configuredApiUrl
  : isLocalHost ? 'http://localhost:8000' : 'https://smc-academy-referral.onrender.com';

class ApiError extends Error {
  constructor(public readonly status: number, message: string, public readonly url: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  if (!API_BASE_URL) throw new Error('The application is not configured correctly.');

  const url = `${API_BASE_URL}${path}`;
  try {
    const response = await fetch(url, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });

    const body = await response.text();
    if (!response.ok) {
      let detail = 'We could not complete that request.';
      try { const parsed = JSON.parse(body) as { detail?: string }; if (parsed.detail) detail = parsed.detail; } catch { /* non-JSON response */ }
      console.error('[api]', { url, status: response.status, detail });
      throw new ApiError(response.status, detail, url);
    }
    console.debug('[api]', { url, status: response.status });
    return JSON.parse(body) as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    console.error('[api-network-error]', { url, error: error instanceof Error ? error.message : 'Unknown error' });
    throw error;
  }
}

function authenticatedHeaders(): HeadersInit {
  const token = sessionToken.get();
  if (!token) throw new Error('Your Telegram session could not be started.');
  return { Authorization: `Bearer ${token}` };
}

export async function authenticateTelegram(initData: string, startParam?: string): Promise<AuthResponse> {
  const response = await request<AuthResponse>('/api/v1/auth/telegram', {
    method: 'POST',
    body: JSON.stringify({ init_data: initData, start_param: startParam || null }),
  });
  sessionToken.set(response.access_token);
  return response;
}

export const getProfile = (): Promise<UserProfileResponse> =>
  request('/api/v1/user/me', { headers: authenticatedHeaders() });

export const getDashboard = (): Promise<DashboardResponse> =>
  request('/api/v1/user/dashboard', { headers: authenticatedHeaders() });

export function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}
