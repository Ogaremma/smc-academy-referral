import { useCallback, useEffect, useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import { adminReferral } from '@/lib/api';
import type { AdminReferral } from '@/types/api';
import { AdminError, AdminLoading } from '@/components/admin/AdminStates';
import { IdentityCell } from '@/components/admin/IdentityCell';
import { StatusBadge } from '@/components/admin/StatusBadge';
import { candidateIdentity, formatDateTime } from '@/components/admin/format';
import { SubmissionFieldValue } from '@/components/SubmissionFields';

interface ReferralDetailPanelProps {
  referralId: number;
  onBack: () => void;
}

export function ReferralDetailPanel({ referralId, onBack }: ReferralDetailPanelProps) {
  const [referral, setReferral] = useState<AdminReferral | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setReferral(await adminReferral(referralId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to load referral details.');
    } finally {
      setLoading(false);
    }
  }, [referralId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading && !referral) return <AdminLoading label="referral details" />;
  if (error && !referral) return <AdminError message="referral details" onRetry={() => void load()} />;
  if (!referral) return null;

  const fields = referral.form_fields ?? [];
  const registrationFields = fields.filter((field) => field.category === 'registration');
  const paymentFields = fields.filter((field) => field.category === 'payment');
  const otherFields = fields.filter(
    (field) => field.category !== 'registration' && field.category !== 'payment',
  );

  return (
    <section className="space-y-5">
      <button type="button" className="icon-button" onClick={onBack} aria-label="Back to referrals">
        <ArrowLeft size={18} />
      </button>

      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-6">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-5">
          <div className="min-w-0">
            <p className="text-xs uppercase tracking-[.16em] text-zinc-500">Referral details</p>
            <h2 className="mt-1 truncate text-xl font-semibold">{candidateIdentity(referral)}</h2>
          </div>
          <StatusBadge status={referral.status} />
        </div>

        <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <div>
            <p className="text-xs text-zinc-500">Affiliate</p>
            <div className="mt-1"><IdentityCell user={referral.referrer} /></div>
          </div>
          <div>
            <p className="text-xs text-zinc-500">Referral code</p>
            <p className="mt-1 font-mono text-sm text-zinc-100">{referral.referral_code || 'Not recorded'}</p>
          </div>
          <div>
            <p className="text-xs text-zinc-500">Submitted</p>
            <p className="mt-1 text-sm text-zinc-100">{formatDateTime(referral.registered_at || referral.created_at)}</p>
          </div>
          <div>
            <p className="text-xs text-zinc-500">Verified</p>
            <p className="mt-1 text-sm text-zinc-100">{referral.verified_at ? formatDateTime(referral.verified_at) : 'Not yet verified'}</p>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-6">
        <h3 className="font-semibold">Registration information</h3>
        <p className="mt-1 text-xs text-zinc-500">Answers submitted through the SMC Academy Google Form.</p>
        {registrationFields.length === 0 ? (
          <p role="status" className="mt-4 text-sm text-zinc-500">
            No registration fields were captured for this submission.
          </p>
        ) : (
          <dl className="mt-5 grid gap-4 sm:grid-cols-2">
            {registrationFields.map((field, index) => (
              <div key={`${field.label}-${index}`} className="min-w-0">
                <dt className="text-xs text-zinc-500">{field.label}</dt>
                <dd className="mt-1"><SubmissionFieldValue field={field} /></dd>
              </div>
            ))}
          </dl>
        )}
      </div>

      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-6">
        <h3 className="font-semibold">Payment verification</h3>
        <p className="mt-1 text-xs text-zinc-500">Review the payment details and proof before approving the referral.</p>
        {paymentFields.length === 0 ? (
          <p role="status" className="mt-4 rounded-lg border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-zinc-400">
            No payment fields were submitted with this referral.
          </p>
        ) : (
          <dl className="mt-5 grid gap-4 sm:grid-cols-2">
            {paymentFields.map((field, index) => (
              <div key={`${field.label}-${index}`} className="min-w-0">
                <dt className="text-xs text-zinc-500">{field.label}</dt>
                <dd className="mt-1"><SubmissionFieldValue field={field} /></dd>
              </div>
            ))}
          </dl>
        )}
      </div>

      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-6">
        <h3 className="font-semibold">Other information</h3>
        <p className="mt-1 text-xs text-zinc-500">Every remaining answer submitted with this referral.</p>
        {otherFields.length === 0 ? (
          <p role="status" className="mt-4 text-sm text-zinc-500">
            No other answers were submitted with this referral.
          </p>
        ) : (
          <dl className="mt-5 grid gap-4 sm:grid-cols-2">
            {otherFields.map((field, index) => (
              <div key={`${field.label}-${index}`} className="min-w-0">
                <dt className="text-xs text-zinc-500">{field.label}</dt>
                <dd className="mt-1"><SubmissionFieldValue field={field} /></dd>
              </div>
            ))}
          </dl>
        )}
      </div>
    </section>
  );
}
