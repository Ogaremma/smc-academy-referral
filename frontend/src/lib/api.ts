import type { AuthResponse, DashboardResponse, UserProfileResponse } from '@/types/api';
import { sessionToken } from '@/lib/session';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '');

class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  if (!API_BASE_URL) throw new Error('The application is not configured correctly.');

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });

  if (!response.ok) {
    throw new ApiError(response.status, 'We could not complete that request.');
  }
  return response.json() as Promise<T>;
}

function authenticatedHeaders(): HeadersInit {
  const token = sessionToken.get();
  if (!token) throw new Error('Your Telegram session could not be started.');
  return { Authorization: `Bearer ${token}` };
}

export async function authenticateTelegram(initData: string): Promise<AuthResponse> {
  const response = await request<AuthResponse>('/api/v1/auth/telegram', {
    method: 'POST',
    body: JSON.stringify({ init_data: initData }),
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
