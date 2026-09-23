import { useCallback, useEffect, useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import {
  ApiError,
  adminAffiliate,
  adminPayout,
  adminReferrals,
  adminRestore,
  adminRevoke,
} from '@/lib/api';
import type { AdminAffiliateDetail, AdminPayout, AdminReferral } from '@/types/api';
import { AdminDataTable } from '@/components/admin/AdminDataTable';
import { AdminError, AdminLoading } from '@/components/admin/AdminStates';
import { AdminKpi } from '@/components/admin/AdminKpi';
import { IdentityCell } from '@/components/admin/IdentityCell';
import { ReferralDetailPanel } from '@/components/admin/ReferralDetailPanel';
import { StatusBadge } from '@/components/admin/StatusBadge';
import { candidateIdentity, formatDate, formatDateTime } from '@/components/admin/format';

interface AffiliateDetailPageProps {
  affiliateId: number;
  onBack: () => void;
  onChanged: () => Promise<void>;
}

export function AffiliateDetailPage({ affiliateId, onBack, onChanged }: AffiliateDetailPageProps) {
  const [affiliate, setAffiliate] = useState<AdminAffiliateDetail | null>(null);
  const [referrals, setReferrals] = useState<AdminReferral[]>([]);
  const [payout, setPayout] = useState<AdminPayout | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionPending, setActionPending] = useState(false);
  const [payoutLoading, setPayoutLoading] = useState(false);
  const [payoutError, setPayoutError] = useState('');
  const [payoutFailed, setPayoutFailed] = useState(false);
  const [selectedReferralId, setSelectedReferralId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [affiliateResponse, referralsResponse] = await Promise.all([
        adminAffiliate(affiliateId),
        adminReferrals(affiliateId),
      ]);
      setAffiliate(affiliateResponse);
      setReferrals(referralsResponse);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to load affiliate details.');
    } finally {
      setLoading(false);
    }
  }, [affiliateId]);

  useEffect(() => {
    void load();
  }, [load]);

  const mutateAffiliate = async (action: 'revoke' | 'restore') => {
    if (actionPending) return;
    const confirmed = window.confirm(
      action === 'revoke'
        ? 'Revoke this affiliate? They cannot register a new affiliate lifecycle until restored.'
        : 'Restore this revoked affiliate to the same lifecycle and referral history?',
    );
    if (!confirmed) return;

    setActionPending(true);
    setError('');
    try {
      if (action === 'revoke') await adminRevoke(affiliateId);
      else await adminRestore(affiliateId);
      await load();
      await onChanged();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to update this affiliate.');
    } finally {
      setActionPending(false);
    }
  };

  const loadPayout = async () => {
    if (payoutLoading) return;
    setPayoutLoading(true);
    setPayoutError('');
    setPayoutFailed(false);
    try {
      setPayout(await adminPayout(affiliateId));
    } catch (caught) {
      setPayout(null);
      if (caught instanceof ApiError && caught.status === 404) {
        setPayoutError('No payout details have been saved for this affiliate.');
      } else if (caught instanceof ApiError && caught.status === 403) {
        setPayoutFailed(true);
        setPayoutError('You do not have permission to view these payout details.');
      } else {
        setPayoutFailed(true);
        setPayoutError('Unable to load payout details. Please try again.');
      }
    } finally {
      setPayoutLoading(false);
    }
  };

  if (loading && !affiliate) return <AdminLoading label="affiliate details" />;
  if (error && !affiliate) return <AdminError message="affiliate details" onRetry={load} />;
  if (!affiliate) return null;

  if (selectedReferralId !== null) {
    return (
      <ReferralDetailPanel
        referralId={selectedReferralId}
        onBack={() => setSelectedReferralId(null)}
      />
    );
  }

  return (
    <section className="space-y-5">
      <button type="button" className="icon-button" onClick={onBack} aria-label="Back to affiliates">
        <ArrowLeft size={18} />
      </button>

      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
        <div className="flex flex-col justify-between gap-4 border-b border-white/10 pb-5 sm:flex-row sm:items-center">
          <div className="flex min-w-0 items-center gap-4">
            <IdentityCell user={affiliate} />
            <StatusBadge status={affiliate.account_status} />
          </div>
          <div className="flex flex-wrap gap-2">
            {affiliate.account_status === 'REVOKED' ? (
              <button type="button" className="primary-button" disabled={actionPending} onClick={() => void mutateAffiliate('restore')}>
                {actionPending ? 'Restoring...' : 'Restore'}
              </button>
            ) : (
              <button
                type="button"
                disabled={actionPending}
                className="rounded-lg border border-rose-400/30 bg-rose-400/10 px-4 py-2.5 text-sm font-semibold text-rose-200 transition hover:bg-rose-400/20 disabled:opacity-50"
                onClick={() => void mutateAffiliate('revoke')}
              >
                {actionPending ? 'Revoking...' : 'Revoke'}
              </button>
            )}
            <button type="button" className="rounded-lg border border-white/10 px-4 py-2.5 text-sm font-medium text-zinc-200 transition hover:bg-white/[0.08]" disabled={payoutLoading} onClick={() => void loadPayout()}>
              {payoutLoading ? 'Loading...' : 'Payout details'}
            </button>
          </div>
        </div>

        {error && <p role="alert" className="mt-4 text-sm text-rose-300">{error}</p>}

        <div className="mt-5 grid gap-4 sm:grid-cols-3">
          <AdminKpi label="Referral code" value={affiliate.referral_code || '—'} />
          <AdminKpi label="Referrals" value={affiliate.referral_count} />
          <AdminKpi label="Joined" value={formatDate(affiliate.created_at)} />
        </div>

        {payoutError && (
          <div
            role={payoutFailed ? 'alert' : 'status'}
            className={`mt-4 rounded-lg border px-4 py-3 text-sm ${
              payoutFailed
                ? 'border-rose-400/25 bg-rose-400/10 text-rose-200'
                : 'border-white/10 bg-white/[0.03] text-zinc-500'
            }`}
          >
            <p>{payoutError}</p>
            {payoutFailed && (
              <button
                type="button"
                className="mt-3 rounded-md border border-white/10 px-3 py-2 text-xs font-medium text-zinc-200 transition hover:bg-white/[0.08]"
                onClick={() => void loadPayout()}
              >
                Retry
              </button>
            )}
          </div>
        )}
        {payout && (
          <div className="mt-5 rounded-lg border border-white/10 bg-black/25 p-4">
            <p className="text-xs font-semibold uppercase tracking-[.14em] text-zinc-500">Payout details</p>
            <dl className="mt-3 grid gap-3 sm:grid-cols-3">
              <div>
                <dt className="text-xs text-zinc-500">Account name</dt>
                <dd className="mt-1 text-sm font-medium">{payout.account_name}</dd>
              </div>
              <div>
                <dt className="text-xs text-zinc-500">Bank</dt>
                <dd className="mt-1 text-sm font-medium">{payout.bank_name}</dd>
              </div>
              <div>
                <dt className="text-xs text-zinc-500">Account number</dt>
                <dd className="mt-1 font-mono text-sm">{payout.account_number}</dd>
              </div>
            </dl>
          </div>
        )}
      </div>

      <div>
        <h2 className="mb-3 font-semibold">Referrals</h2>
        <AdminDataTable
          rows={referrals}
          getKey={(referral) => referral.id}
          emptyTitle="No referrals in this lifecycle"
          emptyMessage="New lifecycle accounts start with zero referrals."
          columns={[
            {
              key: 'candidate',
              header: 'Candidate',
              render: (referral) => <span className="font-medium">{candidateIdentity(referral)}</span>,
            },
            {
              key: 'email',
              header: 'Email',
              render: (referral) => <span className="text-zinc-400">{referral.candidate_email || '—'}</span>,
            },
            {
              key: 'status',
              header: 'Status',
              render: (referral) => <StatusBadge status={referral.status} />,
            },
            {
              key: 'created_at',
              header: 'Date',
              render: (referral) => <span className="text-zinc-400">{formatDateTime(referral.created_at)}</span>,
            },
            {
              key: 'actions',
              header: 'Actions',
              render: (referral) => (
                <button
                  type="button"
                  className="rounded-md border border-white/10 px-3 py-2 text-xs font-medium text-zinc-200 transition hover:bg-white/[0.08]"
                  onClick={() => setSelectedReferralId(referral.id)}
                >
                  View
                </button>
              ),
            },
          ]}
        />
      </div>
    </section>
  );
}
