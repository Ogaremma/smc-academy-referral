import { useCallback, useEffect, useState } from 'react';
import { ArrowLeft, Pencil, RefreshCw, ShieldCheck } from 'lucide-react';
import { ApiError, getPayout, savePayout } from '@/lib/api';
import type { PayoutDetails } from '@/types/api';
import { GlassCard } from '@/components/GlassCard';

const EMPTY_FORM = { account_name: '', bank_name: '', account_number: '' };
const INPUT_CLASS = 'mt-2 min-h-11 w-full rounded-lg border border-white/10 bg-white/[0.04] px-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-teal-300/40 focus:outline-none';

type PayoutStatus = 'loading' | 'ready' | 'empty' | 'error';

export function PayoutDetailsPage({ onBack }: { onBack: () => void }) {
  const [status, setStatus] = useState<PayoutStatus>('loading');
  const [payout, setPayout] = useState<PayoutDetails | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editing, setEditing] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [notice, setNotice] = useState('');

  const load = useCallback(async () => {
    setStatus('loading');
    setLoadError('');
    setNotice('');
    try {
      const response = await getPayout();
      setPayout(response);
      setForm({
        account_name: response.account_name,
        bank_name: response.bank_name,
        account_number: response.account_number,
      });
      setEditing(false);
      setStatus('ready');
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 404) {
        setPayout(null);
        setForm(EMPTY_FORM);
        setEditing(true);
        setStatus('empty');
      } else {
        setLoadError(caught instanceof Error ? caught.message : 'Unable to load your payout details.');
        setStatus('error');
      }
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const update = (key: keyof typeof EMPTY_FORM, value: string) =>
    setForm((current) => ({ ...current, [key]: value }));

  const trimmed = {
    account_name: form.account_name.trim(),
    bank_name: form.bank_name.trim(),
    account_number: form.account_number.trim(),
  };
  const complete =
    trimmed.account_name.length >= 2 &&
    trimmed.bank_name.length >= 2 &&
    trimmed.account_number.length >= 4;

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!complete || saving) return;
    setSaving(true);
    setSaveError('');
    setNotice('');
    try {
      const response = await savePayout(trimmed);
      setPayout(response);
      setForm({
        account_name: response.account_name,
        bank_name: response.bank_name,
        account_number: response.account_number,
      });
      setEditing(false);
      setStatus('ready');
      setNotice('Payout details saved.');
    } catch (caught) {
      setSaveError(caught instanceof Error ? caught.message : 'Unable to save your payout details. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="app-shell min-h-screen px-4 pb-safe pt-safe">
      <div className="relative z-10 mx-auto w-full max-w-lg">
        <div className="flex items-center gap-3">
          <button type="button" className="icon-button" onClick={onBack} aria-label="Back">
            <ArrowLeft size={18} />
          </button>
          <p className="eyebrow">Payouts</p>
        </div>
        <h1 className="section-title mt-4">Payout Details</h1>
        <p className="mt-2 text-sm leading-5 text-zinc-400">Tell SMC Academy where to send your referral payouts.</p>

        {notice && (
          <p role="status" className="mt-4 rounded-lg border border-emerald-400/25 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-200">{notice}</p>
        )}
        {saveError && (
          <p role="alert" className="mt-4 rounded-lg border border-rose-400/25 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">{saveError}</p>
        )}

        {status === 'loading' ? (
          <div className="glass-card mt-5 h-64 animate-pulse" aria-label="Loading payout details" />
        ) : status === 'error' ? (
          <div className="mt-6" role="alert">
            <p className="text-sm text-zinc-300">Unable to load your payout details.</p>
            {loadError && <p className="mt-1 text-xs text-zinc-500">{loadError}</p>}
            <button type="button" className="primary-button mt-4" onClick={() => void load()}>
              <RefreshCw size={16} /> Retry
            </button>
          </div>
        ) : editing ? (
          <GlassCard className="mt-5 p-5">
            {status === 'empty' && (
              <div className="mb-5 flex items-start gap-3 rounded-lg border border-white/10 bg-white/[0.03] p-4">
                <ShieldCheck size={18} className="mt-0.5 shrink-0 text-zinc-400" />
                <p className="text-xs leading-5 text-zinc-400">
                  No payout details yet. Add your account information so payouts are not delayed.
                </p>
              </div>
            )}
            <form onSubmit={submit} noValidate>
              <label className="block" htmlFor="payout-account-name">
                <span className="text-[11px] font-semibold uppercase tracking-[.14em] text-zinc-500">Account name</span>
                <input
                  id="payout-account-name"
                  name="account_name"
                  className={INPUT_CLASS}
                  value={form.account_name}
                  onChange={(event) => update('account_name', event.target.value)}
                  autoComplete="name"
                  placeholder="Name on the bank account"
                />
              </label>
              <label className="mt-4 block" htmlFor="payout-account-number">
                <span className="text-[11px] font-semibold uppercase tracking-[.14em] text-zinc-500">Account number</span>
                <input
                  id="payout-account-number"
                  name="account_number"
                  className={INPUT_CLASS}
                  value={form.account_number}
                  onChange={(event) => update('account_number', event.target.value)}
                  inputMode="numeric"
                  autoComplete="off"
                  placeholder="0123456789"
                />
              </label>
              <label className="mt-4 block" htmlFor="payout-bank-name">
                <span className="text-[11px] font-semibold uppercase tracking-[.14em] text-zinc-500">Bank name</span>
                <input
                  id="payout-bank-name"
                  name="bank_name"
                  className={INPUT_CLASS}
                  value={form.bank_name}
                  onChange={(event) => update('bank_name', event.target.value)}
                  autoComplete="organization"
                  placeholder="e.g. Access Bank"
                />
              </label>
              <button type="submit" className="primary-button mt-5 w-full" disabled={!complete || saving}>
                {saving ? 'Saving...' : 'Save payout details'}
              </button>
            </form>
          </GlassCard>
        ) : (
          <GlassCard className="mt-5 p-5">
            <div className="flex items-center justify-between gap-4">
              <p className="eyebrow">Saved account</p>
              <button type="button" className="icon-button" onClick={() => setEditing(true)} aria-label="Edit payout details">
                <Pencil size={16} />
              </button>
            </div>
            <dl className="mt-4 divide-y divide-white/[0.07]">
              <div className="py-3 first:pt-0">
                <dt className="text-[11px] font-semibold uppercase tracking-[.14em] text-zinc-500">Account name</dt>
                <dd className="mt-1 text-sm font-medium text-zinc-100">{payout?.account_name}</dd>
              </div>
              <div className="py-3">
                <dt className="text-[11px] font-semibold uppercase tracking-[.14em] text-zinc-500">Bank name</dt>
                <dd className="mt-1 text-sm font-medium text-zinc-100">{payout?.bank_name}</dd>
              </div>
              <div className="py-3 last:pb-0">
                <dt className="text-[11px] font-semibold uppercase tracking-[.14em] text-zinc-500">Account number</dt>
                <dd className="mt-1 font-mono text-sm text-zinc-100">{payout?.account_number}</dd>
              </div>
            </dl>
          </GlassCard>
        )}
      </div>
    </main>
  );
}
