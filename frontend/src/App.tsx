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
import { deleteAccount, getReferrals, getReferral } from '@/lib/api';
import { setTelegramBackButton } from '@/lib/telegram';

function App() {
  const { state, retry } = useDashboard();
  const [unlocked, setUnlocked] = useState(false);
  const [page, setPage] = useState(false); const [refs, setRefs] = useState<any>(null); const [detail, setDetail] = useState<any>(null); const [deleting, setDeleting] = useState(false);
  const userTelegramId = state.status === 'ready' ? state.data.profile.user.telegram_id : null;
  const storageKey = useMemo(() => userTelegramId ? `smc_referral_unlocked_${userTelegramId}` : null, [userTelegramId]);

  useEffect(() => {
    setUnlocked(storageKey ? localStorage.getItem(storageKey) === '1' : false);
  }, [storageKey]);
  useEffect(() => setTelegramBackButton(page, () => { if (detail) setDetail(null); else setPage(false); }), [page, detail]);

  if (state.status === 'loading') {
    return <DashboardSkeleton />;
  }

  if (state.status === 'error') {
    return <ErrorState message={state.message} onRetry={retry} />;
  }

  const { profile, dashboard } = state.data;
  if (page) return <main className="app-shell min-h-screen px-4 pt-safe"><button className="icon-button" onClick={()=>setPage(false)}>Back</button><h1 className="section-title mt-5">My Referrals</h1>{!refs ? <button className="primary-button mt-5" onClick={()=>getReferrals().then(setRefs)}>Load referrals</button> : refs.referrals.length===0 ? <p className="mt-6 text-zinc-400">No Referrals Yet</p> : refs.referrals.map((r:any)=><button className="glass-card mt-3 w-full p-4 text-left" key={r.id} onClick={()=>getReferral(r.id).then(setDetail)}><b>{r.name}</b><div className="text-sm text-zinc-400">{r.course || 'Course not specified'} · {r.status}</div></button>)}{detail && <div className="glass-card mt-5 p-4">{Object.entries(detail.fields).map(([k,v])=><p key={k} className="text-sm">{k}: {String(v)}</p>)}</div>}</main>;
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
            <p className="eyebrow mt-7">Your private invite</p><h1 className="mt-2 text-xl font-semibold">Sign Up As an SMC Academy Affiliate</h1>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight text-white">Build your circle.</h2>
            <p className="mx-auto mt-4 max-w-xs text-sm leading-6 text-zinc-400">Your Telegram account is securely connected. Generate your unique referral link and invite others to join the next SMC Academy cohort.</p>
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
          <ReferralLinkCard link={dashboard.personal_referral_link} />
          <ReferralCodeCard code={profile.referral_code} />
          <button className="icon-button w-full" onClick={()=>{setPage(true); void getReferrals().then(setRefs)}}>View All Referrals</button><button className="mt-3 w-full rounded-md bg-red-950 px-4 py-3 text-red-200" onClick={()=>setDeleting(true)}>Delete Account</button>
        </section>

        <ActivityList items={dashboard.recent_verified_activity} />

        <footer className="pb-5 pt-8 text-center text-xs text-zinc-600">
          SMC Academy Referral Programme
        </footer>
      </div>
      {deleting && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-5"><div className="glass-card p-6"><h2 className="text-lg font-semibold">Delete Affiliate Account?</h2><p className="mt-3 text-sm text-zinc-400">Are you sure you want to delete your SMC Academy affiliate account? Your affiliate account and referral access will be permanently removed.</p><div className="mt-5 flex gap-3"><button className="icon-button" onClick={()=>setDeleting(false)}>Cancel</button><button className="rounded-md bg-red-600 px-3 py-2" onClick={()=>void deleteAccount().then(()=>window.location.reload())}>Delete Account</button></div></div></div>}
    </main>
  );
}

export default App;
