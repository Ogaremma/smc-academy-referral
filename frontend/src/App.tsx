import { useDashboard } from '@/hooks/useDashboard';
import { ActivityList } from '@/components/ActivityList';
import { AppHeader } from '@/components/AppHeader';
import { DashboardSkeleton } from '@/components/DashboardSkeleton';
import { ErrorState } from '@/components/ErrorState';
import { MyReferralsPage } from '@/components/MyReferralsPage';
import { PayoutDetailsPage } from '@/components/PayoutDetailsPage';
import { ReferralCodeCard } from '@/components/ReferralCodeCard';
import { ReferralLinkCard } from '@/components/ReferralLinkCard';
import { RegistrationFormCard } from '@/components/RegistrationFormCard';
import { StatCard } from '@/components/StatCard';
import { Sparkles, Users, Wallet } from 'lucide-react';
import { useEffect, useState } from 'react';
import { deleteAccount } from '@/lib/api';
import { setTelegramBackButton } from '@/lib/telegram';
import { AdminDashboard } from '@/components/AdminDashboard';

type AffiliateView = 'dashboard' | 'referrals' | 'payout';

function App() {
  const { state, retry, register } = useDashboard();
  const [view, setView] = useState<AffiliateView>('dashboard');
  const [deleting, setDeleting] = useState<'idle' | 'busy' | boolean>(false);
  const [deleteError, setDeleteError] = useState('');
  const [deleted, setDeleted] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [registerError, setRegisterError] = useState('');
  const [adminMode, setAdminMode] = useState(false);

  useEffect(() => setTelegramBackButton(view !== 'dashboard', () => setView('dashboard')), [view]);

  if (state.status === 'loading') return <DashboardSkeleton />;
  if (state.status === 'error') return <ErrorState message={state.message} onRetry={retry} />;
  if (deleted) return <main className="app-shell flex min-h-screen items-center justify-center px-4"><section className="glass-card w-full max-w-md p-7 text-center"><h1 className="text-2xl font-semibold">Account Deleted</h1><p className="mt-3 text-sm text-zinc-400">Your affiliate account has been deactivated. You can close this Mini App.</p></section></main>;
  if (state.status === 'onboarding') return <main className="app-shell flex min-h-screen items-center justify-center px-4 pb-safe pt-safe"><section className="relative z-10 w-full max-w-md"><AppHeader firstName={state.auth.user?.first_name ?? null} photoUrl={state.auth.user?.photo_url ?? null} /><div className="glass-card mt-10 overflow-hidden p-7 text-center sm:p-10"><div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-white/15 bg-white text-black"><Sparkles size={24} /></div><p className="eyebrow mt-7">Your private invite</p><h1 className="mt-2 text-xl font-semibold">Sign Up As an SMC Academy Affiliate</h1><h2 className="mt-2 text-3xl font-semibold text-white">Build your circle.</h2><p className="mx-auto mt-4 max-w-xs text-sm leading-6 text-zinc-400">Your Telegram account is securely connected. Generate your unique referral link and invite others to join the next SMC Academy cohort.</p>{registerError && <p role="alert" className="mt-3 text-sm text-red-300">{registerError}</p>}<button type="button" className="primary-button mt-8 w-full py-3.5 text-base" disabled={registering} onClick={async()=>{setRegistering(true);setRegisterError('');try{await register();}catch(e){setRegisterError(e instanceof Error?e.message:'Unable to create your affiliate account.');}finally{setRegistering(false);}}}>{registering ? 'Generating...' : 'Generate My Unique Link'}</button></div></section></main>;
  if (adminMode && state.data.profile.user.is_admin) return <AdminDashboard admin={state.data.profile.user} onBack={()=>setAdminMode(false)} />;

  if (view === 'referrals') return <MyReferralsPage onBack={() => setView('dashboard')} />;
  if (view === 'payout') return <PayoutDetailsPage onBack={() => setView('dashboard')} />;

  const { profile, dashboard } = state.data;
  return (
    <main className="app-shell animate-fade-in">
      <div className="relative z-10 mx-auto w-full max-w-lg px-4 pb-safe pt-safe sm:px-6">
        <AppHeader firstName={profile.user.first_name} photoUrl={profile.user.photo_url} />
        {profile.user.is_admin && <button type="button" className="primary-button mt-4 w-full" onClick={() => setAdminMode(true)}>Admin Dashboard</button>}
        <section className="mt-8"><StatCard value={dashboard.total_verified_referrals} /></section>
        <section className="mt-4 grid gap-4" aria-label="Referral tools">
          {dashboard.registration_form_url && <RegistrationFormCard url={dashboard.registration_form_url} />}
          <ReferralLinkCard link={dashboard.personal_referral_link} />
          <ReferralCodeCard code={profile.referral_code} />
          <div className="grid gap-3 sm:grid-cols-2">
            <button type="button" className="icon-button w-full gap-2 px-3 text-sm" onClick={() => setView('referrals')}>
              <Users size={17} /> View All Referrals
            </button>
            <button type="button" className="icon-button w-full gap-2 px-3 text-sm" onClick={() => setView('payout')}>
              <Wallet size={17} /> Payout Details
            </button>
          </div>
          <button type="button" className="w-full rounded-md bg-red-950 px-4 py-3 text-red-200" onClick={() => setDeleting(true)}>Delete Account</button>
        </section>
        <ActivityList items={dashboard.recent_verified_activity} />
      </div>
      {deleting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-5">
          <div className="glass-card p-6">
            <h2 className="text-lg font-semibold">Delete Affiliate Account?</h2>
            <p className="mt-3 text-sm text-zinc-400">Your affiliate account will be deactivated. Historical referral records are preserved.</p>
            {deleteError && <p role="alert" className="mt-3 text-sm text-red-300">{deleteError}</p>}
            <div className="mt-5 flex gap-3">
              <button type="button" className="icon-button" disabled={deleting === 'busy'} onClick={() => setDeleting(false)}>Cancel</button>
              <button
                type="button"
                className="rounded-md bg-red-600 px-3 py-2 disabled:opacity-50"
                disabled={deleting === 'busy'}
                onClick={async () => {
                  setDeleting('busy');
                  setDeleteError('');
                  try {
                    await deleteAccount();
                    setDeleting(false);
                    setDeleted(true);
                  } catch (error) {
                    setDeleting(true);
                    setDeleteError(error instanceof Error ? error.message : 'Unable to delete account. Please try again.');
                  }
                }}
              >
                {deleting === 'busy' ? 'Deleting...' : 'Delete Account'}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
export default App;
