import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({ authenticate: vi.fn(), profile: vi.fn(), dashboard: vi.fn() }));
vi.mock('@/lib/api', () => ({ authenticateTelegram: mocks.authenticate, getProfile: mocks.profile, getDashboard: mocks.dashboard, isUnauthorized: () => false }));
vi.mock('@/lib/telegram', () => ({ initializeTelegram: () => ({ initData: 'signed-init-data' }), getTelegramStartParam: () => undefined }));
import { useDashboard } from '@/hooks/useDashboard';

const profile = { user: { telegram_id: 1 }, referral_code: 'SMC-ABC' };
const dashboard = { total_verified_referrals: 0, recent_verified_activity: [], personal_referral_link: 'x' };
beforeEach(() => { sessionStorage.clear(); vi.clearAllMocks(); });

it('retries transient authentication failures and stops after success', async () => {
  mocks.authenticate.mockRejectedValueOnce(new Error('one')).mockRejectedValueOnce(new Error('two')).mockResolvedValueOnce({ affiliate_active: true });
  mocks.profile.mockResolvedValue(profile); mocks.dashboard.mockResolvedValue(dashboard);
  const { result } = renderHook(() => useDashboard());
  await waitFor(() => expect(result.current.state.status).toBe('ready'), { timeout: 4000 });
  expect(mocks.authenticate).toHaveBeenCalledTimes(3);
});

it('bounds failed authentication at three attempts', async () => {
  mocks.authenticate.mockRejectedValue(new Error('offline'));
  const { result } = renderHook(() => useDashboard());
  await waitFor(() => expect(result.current.state.status).toBe('error'), { timeout: 4000 });
  expect(mocks.authenticate).toHaveBeenCalledTimes(3);
});
