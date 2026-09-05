import { beforeEach, expect, it, vi } from 'vitest';
import { authenticateTelegram, deleteAccount, registerAffiliate } from '@/lib/api';

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

it('authenticates without creating an affiliate and registers only explicitly', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(new Response(JSON.stringify({ access_token: 'telegram-token', affiliate_active: false }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ access_token: 'affiliate-token', affiliate_active: true }), { status: 200 }));
  await authenticateTelegram('signed-init', 'start-code');
  expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toMatchObject({ init_data: 'signed-init', start_param: 'start-code', create_account: false });
  await registerAffiliate();
  expect(String(fetchMock.mock.calls[1][0])).toContain('/api/v1/auth/affiliate/register');
  expect(fetchMock.mock.calls[1][1]?.headers).toMatchObject({ Authorization: 'Bearer telegram-token' });
});
