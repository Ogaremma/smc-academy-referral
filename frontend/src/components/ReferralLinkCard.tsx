import { Check, Copy, Send } from 'lucide-react';
import { useCopy } from '@/hooks/useCopy';
import { shareOnTelegram } from '@/lib/telegram';
import { GlassCard } from './GlassCard';

export function ReferralLinkCard({ link }: { link: string }) {
  const { copied, copy } = useCopy();
  return (
    <GlassCard className="p-5">
      <div className="flex items-center justify-between"><div><p className="eyebrow">Personal link</p><h2 className="mt-1 text-base font-semibold text-white">Invite someone</h2></div><Send size={18} className="text-zinc-300" aria-hidden="true" /></div>
      <p className="mt-4 break-all rounded-md border border-white/[0.07] bg-black/20 p-3 text-xs leading-5 text-zinc-400">{link}</p>
      <p className="mt-3 text-xs leading-5 text-zinc-500">Share this link. Completed registrations through the form count as your referrals.</p>
      <div className="mt-4 grid grid-cols-2 gap-2.5">
        <button type="button" className="icon-button w-full gap-2 px-3 text-sm" onClick={() => void copy(link)} aria-label="Copy personal referral link">
          {copied ? <Check size={17} className="text-zinc-200" /> : <Copy size={17} />} {copied ? 'Copied' : 'Copy link'}
        </button>
        <button type="button" className="primary-button" onClick={() => shareOnTelegram(link)} aria-label="Share personal referral link on Telegram"><Send size={17} /> Share</button>
      </div>
    </GlassCard>
  );
}
