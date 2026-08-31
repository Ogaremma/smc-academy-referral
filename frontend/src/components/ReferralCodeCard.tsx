import { Check, Copy, KeyRound } from 'lucide-react';
import { useCopy } from '@/hooks/useCopy';
import { GlassCard } from './GlassCard';

export function ReferralCodeCard({ code }: { code: string }) {
  const { copied, copy } = useCopy();
  return (
    <GlassCard className="p-5">
      <div className="flex items-center gap-2 text-zinc-400"><KeyRound size={16} aria-hidden="true" /><h2 className="text-xs font-medium uppercase tracking-[.14em]">Referral code</h2></div>
      <div className="mt-4 flex items-center gap-3">
        <code className="min-w-0 flex-1 overflow-hidden text-ellipsis whitespace-nowrap text-xl font-semibold text-white">{code}</code>
        <button type="button" className="icon-button" onClick={() => void copy(code)} aria-label={copied ? 'Referral code copied' : 'Copy referral code'} title="Copy referral code">
          {copied ? <Check size={18} className="text-emerald-300" /> : <Copy size={18} />}
        </button>
      </div>
      <p className="mt-3 min-h-5 text-xs text-emerald-300/80" aria-live="polite">{copied ? 'Code copied to clipboard' : 'Share this code with a prospective student.'}</p>
    </GlassCard>
  );
}
