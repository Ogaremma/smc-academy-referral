import { useCallback, useEffect, useState } from 'react';
import { authenticateTelegram, getDashboard, getProfile, isUnauthorized, registerAffiliate } from '@/lib/api';
import { getTelegramStartParam, initializeTelegram } from '@/lib/telegram';
import { sessionToken } from '@/lib/session';
import type { DashboardData } from '@/types/api';

type DashboardState =
  | { status: 'loading' }
  | { status: 'ready'; data: DashboardData }
  | { status: 'onboarding'; auth: import('@/types/api').AuthResponse }
  | { status: 'error'; message: string };

async function loadAuthenticatedData(initData: string, startParam?: string): Promise<DashboardData | { onboarding: import('@/types/api').AuthResponse }> {
  if (!sessionToken.get()) {
    const auth = await authenticateTelegram(initData, startParam);
    if (!auth.affiliate_active) return { onboarding: auth };
  }

  try {
    const [profile, dashboard] = await Promise.all([getProfile(), getDashboard()]);
    return { profile, dashboard };
  } catch (error) {
    if (!isUnauthorized(error)) throw error;
    sessionToken.clear();
    await authenticateTelegram(initData, startParam);
    const [profile, dashboard] = await Promise.all([getProfile(), getDashboard()]);
    return { profile, dashboard };
  }
}

export function useDashboard(): { state: DashboardState; retry: () => void; register: () => Promise<void> } {
  const [state, setState] = useState<DashboardState>({ status: 'loading' });
  const [attempt, setAttempt] = useState(0);

  const retry = useCallback(() => {
    sessionToken.clear();
    setState({ status: 'loading' });
    setAttempt((value) => value + 1);
  }, []);
  const register = useCallback(async () => {
    await registerAffiliate();
    const [profile, dashboard] = await Promise.all([getProfile(), getDashboard()]);
    setState({ status: 'ready', data: { profile, dashboard } });
  }, []);

  useEffect(() => {
    let active = true;
    const webApp = initializeTelegram();
    const initData = webApp?.initData ?? '';
    console.info('[telegram-auth]', { webAppAvailable: Boolean(webApp), initDataPresent: Boolean(initData), initDataLength: initData.length });
    const startParam = webApp ? getTelegramStartParam(webApp) : undefined;

    if (!initData) {
      setState({ status: 'error', message: 'Open this Mini App from @SMCARtrackerbot in Telegram to continue.' });
      return () => { active = false; };
    }

    const run = async () => { let last: unknown; for (let i=0;i<3;i++) { try { return await loadAuthenticatedData(initData, startParam); } catch(e) { last=e; if(i<2) await new Promise(r=>setTimeout(r, 500 * 2 ** i)); } } throw last; };
    run()
      .then((data) => { if (active) setState('onboarding' in data ? { status: 'onboarding', auth: data.onboarding } : { status: 'ready', data }); })
      .catch((error: unknown) => {
        console.error('[dashboard-load-failed]', error);
        if (active) setState({ status: 'error', message: 'We could not load your referral dashboard. Check the browser console for the request status and try again.' });
      });

    return () => { active = false; };
  }, [attempt]);

  return { state, retry, register };
}
