import { beforeEach, expect, it, vi } from 'vitest';
import { deleteAccount } from '@/lib/api';

beforeEach(() => { sessionStorage.clear(); vi.restoreAllMocks(); });

it('sends authenticated DELETE and clears the session after 204', async () => {
  sessionStorage.setItem('smc_referral_session_token', 'test-token');
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 204 }));
  await deleteAccount();
  expect(fetchMock).toHaveBeenCalledOnce();
  const [url, options] = fetchMock.mock.calls[0];
  expect(String(url)).toContain('/api/v1/auth/account');
  expect(options?.method).toBe('DELETE');
  expect(options?.headers).toMatchObject({ Authorization: 'Bearer test-token' });
  expect(sessionStorage.getItem('smc_referral_session_token')).toBeNull();
});
