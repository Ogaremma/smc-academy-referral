import { useDashboard } from '@/hooks/useDashboard';
import { ActivityList } from '@/components/ActivityList';
import { AppHeader } from '@/components/AppHeader';
import { DashboardSkeleton } from '@/components/DashboardSkeleton';
import { ErrorState } from '@/components/ErrorState';
import { ReferralCodeCard } from '@/components/ReferralCodeCard';
import { ReferralLinkCard } from '@/components/ReferralLinkCard';
import { RegistrationFormCard } from '@/components/RegistrationFormCard';
import { StatCard } from '@/components/StatCard';
import { ArrowUpRight, Link2, Sparkles } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

function App() {
  const { state, retry } = useDashboard();
  const [unlocked, setUnlocked] = useState(false);
  const userTelegramId = state.status === 'ready' ? state.data.profile.user.telegram_id : null;
  const storageKey = useMemo(() => userTelegramId ? `smc_referral_unlocked_${userTelegramId}` : null, [userTelegramId]);

  useEffect(() => {
    setUnlocked(storageKey ? localStorage.getItem(storageKey) === '1' : false);
  }, [storageKey]);

  if (state.status === 'loading') {
    return <DashboardSkeleton />;
  }

  if (state.status === 'error') {
    return <ErrorState message={state.message} onRetry={retry} />;
  }

  const { profile, dashboard } = state.data;
  const revealReferral = () => {
    if (storageKey) localStorage.setItem(storageKey, '1');
    setUnlocked(true);
  };

  if (!unlocked) {
    return (
      <main className="app-shell flex min-h-screen items-center justify-center px-4 pb-safe pt-safe">
        <div className="ambient ambient-top" aria-hidden="true" />
        <section className="relative z-10 w-full max-w-md animate-slide-up">
          <AppHeader firstName={profile.user.first_name} photoUrl={profile.user.photo_url} />
          <div className="glass-card mt-10 overflow-hidden p-7 text-center sm:p-10">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-white/15 bg-white text-black shadow-[0_0_35px_rgba(255,255,255,.12)]"><Sparkles size={24} /></div>
            <p className="eyebrow mt-7">Your private invite</p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight text-white">Build your circle.</h2>
            <p className="mx-auto mt-4 max-w-xs text-sm leading-6 text-zinc-400">Your account is connected securely through Telegram. Generate your unique link to invite friends into the next SMC Academy cohort.</p>
            <button type="button" className="primary-button mt-8 w-full py-3.5 text-base" onClick={revealReferral}><Link2 size={18} /> Generate My Referral Link <ArrowUpRight size={17} /></button>
          </div>
          <p className="mt-6 text-center text-[11px] uppercase tracking-[.2em] text-zinc-600">SMC Academy · Referral Programme</p>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell animate-fade-in">
      <div className="ambient ambient-top" aria-hidden="true" />
      <div className="ambient ambient-side" aria-hidden="true" />

      <div className="relative z-10 mx-auto w-full max-w-lg px-4 pb-safe pt-safe sm:px-6">
        <AppHeader firstName={profile.user.first_name} photoUrl={profile.user.photo_url} />

        <section className="mt-8" aria-labelledby="overview-heading">
          <div className="mb-3 flex items-end justify-between gap-4">
            <div>
              <p className="eyebrow">Your impact</p>
              <h2 id="overview-heading" className="section-title">Referral overview</h2>
            </div>
            <span className="live-badge"><span /> Live</span>
          </div>
          <StatCard value={dashboard.total_verified_referrals} />
        </section>

        <section className="mt-4 grid gap-4" aria-label="Referral tools">
          {dashboard.registration_form_url && (
            <RegistrationFormCard url={dashboard.registration_form_url} />
          )}
          <ReferralCodeCard code={profile.referral_code} />
          <ReferralLinkCard link={dashboard.personal_referral_link} />
        </section>

        <ActivityList items={dashboard.recent_verified_activity} />

        <footer className="pb-5 pt-8 text-center text-xs text-zinc-600">
          SMC Academy Referral Programme
        </footer>
      </div>
    </main>
  );
}

export default App;
