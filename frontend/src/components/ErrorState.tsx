import { RefreshCw, ShieldAlert } from 'lucide-react';
import { hapticTap } from '@/lib/telegram';
import { GlassCard } from './GlassCard';

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  const retry = () => { hapticTap(); onRetry(); };
  return <main className="app-shell flex items-center justify-center px-4 pb-safe pt-safe"><div className="ambient ambient-top" /><GlassCard className="relative z-10 w-full max-w-sm p-7 text-center"><div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg border border-white/15 bg-white/[0.07] text-zinc-200"><ShieldAlert size={22} /></div><h1 className="mt-5 text-xl font-semibold text-white">Unable to connect</h1><p className="mt-2 text-sm leading-6 text-zinc-400">{message}</p><button type="button" className="primary-button mt-6 w-full" onClick={retry}><RefreshCw size={17} /> Try again</button><p className="mt-4 text-xs text-zinc-600">SMC Academy Referral Portal</p></GlassCard></main>;
}
