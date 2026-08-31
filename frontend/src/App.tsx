import { useDashboard } from '@/hooks/useDashboard';
import { ActivityList } from '@/components/ActivityList';
import { AppHeader } from '@/components/AppHeader';
import { DashboardSkeleton } from '@/components/DashboardSkeleton';
import { ErrorState } from '@/components/ErrorState';
import { ReferralCodeCard } from '@/components/ReferralCodeCard';
import { ReferralLinkCard } from '@/components/ReferralLinkCard';
import { StatCard } from '@/components/StatCard';

function App() {
  const { state, retry } = useDashboard();

  if (state.status === 'loading') {
    return <DashboardSkeleton />;
  }

  if (state.status === 'error') {
    return <ErrorState message={state.message} onRetry={retry} />;
  }

  const { profile, dashboard } = state.data;

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
