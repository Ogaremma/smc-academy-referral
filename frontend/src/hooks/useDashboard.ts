import { useCallback, useEffect, useState } from 'react';
import { authenticateTelegram, getDashboard, getProfile, isUnauthorized } from '@/lib/api';
import { initializeTelegram } from '@/lib/telegram';
import { sessionToken } from '@/lib/session';
import type { DashboardData } from '@/types/api';

type DashboardState =
  | { status: 'loading' }
  | { status: 'ready'; data: DashboardData }
  | { status: 'error'; message: string };

async function loadAuthenticatedData(initData: string): Promise<DashboardData> {
  if (!sessionToken.get()) await authenticateTelegram(initData);

  try {
    const [profile, dashboard] = await Promise.all([getProfile(), getDashboard()]);
    return { profile, dashboard };
  } catch (error) {
    if (!isUnauthorized(error)) throw error;
    sessionToken.clear();
    await authenticateTelegram(initData);
    const [profile, dashboard] = await Promise.all([getProfile(), getDashboard()]);
    return { profile, dashboard };
  }
}

export function useDashboard(): { state: DashboardState; retry: () => void } {
  const [state, setState] = useState<DashboardState>({ status: 'loading' });
  const [attempt, setAttempt] = useState(0);

  const retry = useCallback(() => {
    sessionToken.clear();
    setState({ status: 'loading' });
    setAttempt((value) => value + 1);
  }, []);

  useEffect(() => {
    let active = true;
    const webApp = initializeTelegram();
    const initData = webApp?.initData ?? '';

    if (!initData) {
      setState({ status: 'error', message: 'Open this Mini App from @SMCARtrackerbot in Telegram to continue.' });
      return () => { active = false; };
    }

    loadAuthenticatedData(initData)
      .then((data) => { if (active) setState({ status: 'ready', data }); })
      .catch(() => {
        if (active) setState({ status: 'error', message: 'We could not load your referral dashboard. Check your connection and try again.' });
      });

    return () => { active = false; };
  }, [attempt]);

  return { state, retry };
}
