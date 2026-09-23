import { useCallback, useEffect, useState } from 'react';
import { ArrowLeft, ChevronRight, Inbox, RefreshCw, UserRound } from 'lucide-react';
import { getReferral, getReferrals } from '@/lib/api';
import type { ReferralDetail, ReferralSummary } from '@/types/api';
import { GlassCard } from '@/components/GlassCard';
import { StatusBadge } from '@/components/StatusBadge';
import { SubmissionFieldValue, groupSubmissionFields } from '@/components/SubmissionFields';

function formatDate(value: string | null): string {
  if (!value) return 'Recently';
  return new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(value));
}

function contactLine(referral: ReferralSummary): string {
  const parts = [referral.email, referral.telegram].filter(Boolean);
  return parts.length > 0 ? parts.join(' • ') : 'No contact captured';
}

export function MyReferralsPage({ onBack }: { onBack: () => void }) {
  const [referrals, setReferrals] = useState<ReferralSummary[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [detailId, setDetailId] = useState<number | null>(null);
  const [detail, setDetail] = useState<ReferralDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await getReferrals();
      setReferrals(response.referrals);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to load your referrals.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const openDetail = async (id: number) => {
    setDetailId(id);
    setDetail(null);
    setDetailError('');
    setDetailLoading(true);
    try {
      setDetail(await getReferral(id));
    } catch (caught) {
      setDetailError(caught instanceof Error ? caught.message : 'Unable to load referral details.');
    } finally {
      setDetailLoading(false);
    }
  };

  const closeDetail = () => {
    setDetailId(null);
    setDetail(null);
    setDetailError('');
  };

  const goBack = () => {
    if (detailId !== null) closeDetail();
    else onBack();
  };

  const sections = detail ? groupSubmissionFields(detail.form_fields ?? []) : [];

  return (
    <main className="app-shell min-h-screen px-4 pb-safe pt-safe">
      <div className="relative z-10 mx-auto w-full max-w-lg">
        <div className="flex items-center gap-3">
          <button type="button" className="icon-button" onClick={goBack} aria-label="Back">
            <ArrowLeft size={18} />
          </button>
          <p className="eyebrow">{detailId !== null ? 'Referral' : 'Your network'}</p>
        </div>
        <h1 className="section-title mt-4">{detailId !== null ? 'Referral Details' : 'My Referrals'}</h1>

        {detailId !== null ? (
          detailLoading ? (
            <div className="glass-card mt-5 h-56 animate-pulse" aria-label="Loading referral details" />
          ) : detailError ? (
            <div className="mt-6" role="alert">
              <p className="text-sm text-zinc-300">Unable to load referral details.</p>
              <button type="button" className="primary-button mt-4" onClick={() => void openDetail(detailId)}>Retry</button>
            </div>
          ) : detail ? (
            <GlassCard className="mt-5 p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <p className="eyebrow">Registration</p>
                  <h2 className="mt-1 truncate text-lg font-semibold text-white">{detail.name || 'Referred student'}</h2>
                  <p className="mt-1 truncate text-xs text-zinc-400">{contactLine(detail)}</p>
                  <p className="mt-1 text-xs text-zinc-500">Submitted {formatDate(detail.registered_at || detail.created_at)}</p>
                </div>
                <StatusBadge status={detail.status} />
              </div>

              {sections.length === 0 ? (
                <p className="mt-5 rounded-md border border-white/[0.07] bg-black/20 p-3 text-sm text-zinc-400">
                  No additional registration details were captured for this referral.
                </p>
              ) : (
                sections.map((section) => (
                  <section key={section.key} className="mt-5 border-t border-white/[0.07] pt-4" aria-label={section.title}>
                    <h3 className="text-[11px] font-semibold uppercase tracking-[.14em] text-zinc-500">{section.title}</h3>
                    <dl className="mt-3 divide-y divide-white/[0.07]">
                      {section.fields.map((field, index) => (
                        <div key={`${field.label}-${index}`} className="py-3 first:pt-0 last:pb-0">
                          <dt className="text-[11px] font-semibold uppercase tracking-[.14em] text-zinc-500">{field.label}</dt>
                          <dd className="mt-1 break-words text-sm text-zinc-200">
                            <SubmissionFieldValue field={field} />
                          </dd>
                        </div>
                      ))}
                    </dl>
                  </section>
                ))
              )}
            </GlassCard>
          ) : null
        ) : loading ? (
          <div className="glass-card mt-5 h-64 animate-pulse" aria-label="Loading referrals" />
        ) : error ? (
          <div className="mt-6" role="alert">
            <p className="text-sm text-zinc-300">Unable to load your referrals.</p>
            <button type="button" className="primary-button mt-4" onClick={() => void load()}><RefreshCw size={16} /> Retry</button>
          </div>
        ) : !referrals ? null : referrals.length === 0 ? (
          <GlassCard className="mt-5 flex flex-col items-center px-6 py-10 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-white/10 bg-white/[0.05] text-zinc-400"><Inbox size={22} /></div>
            <h2 className="mt-4 text-lg font-semibold text-white">No Referrals Yet</h2>
            <p className="mt-2 max-w-xs text-sm leading-5 text-zinc-400">Share your referral link to start building your network.</p>
          </GlassCard>
        ) : (
          <>
            <p className="mt-2 text-sm text-zinc-400">
              {referrals.length} {referrals.length === 1 ? 'referral' : 'referrals'} registered through your link
            </p>
            <section className="mt-4 space-y-3" aria-label="Your referrals">
              {referrals.map((referral) => (
                <button
                  key={referral.id}
                  type="button"
                  className="glass-card flex w-full items-center gap-3 p-4 text-left transition hover:border-white/20"
                  onClick={() => void openDetail(referral.id)}
                  aria-label={`Open referral ${referral.name}`}
                >
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/[0.08] text-zinc-300"><UserRound size={18} /></span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium text-zinc-100">{referral.name}</span>
                    <span className="mt-0.5 block truncate text-xs text-zinc-500">{referral.course || 'Course not specified'}</span>
                    <span className="mt-0.5 block truncate text-xs text-zinc-600">
                      {contactLine(referral)} • {formatDate(referral.registered_at || referral.created_at)}
                    </span>
                  </span>
                  <span className="flex shrink-0 items-center gap-2">
                    <StatusBadge status={referral.status} />
                    <ChevronRight size={16} className="text-zinc-600" />
                  </span>
                </button>
              ))}
            </section>
          </>
        )}
      </div>
    </main>
  );
}
