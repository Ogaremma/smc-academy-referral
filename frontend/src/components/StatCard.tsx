import { BadgeCheck } from 'lucide-react';
import { GlassCard } from './GlassCard';

export function StatCard({ value }: { value: number }) {
  return (
    <GlassCard className="relative overflow-hidden p-5">
      <div className="absolute inset-y-0 right-0 w-36 bg-[radial-gradient(circle_at_center,rgba(255,255,255,.1),transparent_68%)]" aria-hidden="true" />
      <div className="relative flex items-center justify-between gap-5">
        <div>
          <p className="text-4xl font-semibold tabular-nums text-white">{value.toLocaleString()}</p>
          <p className="mt-1 text-sm font-medium text-zinc-300">Verified registrations</p>
          <p className="mt-2 text-xs leading-5 text-zinc-500">Confirmed SMC Academy form submissions</p>
        </div>
        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-lg border border-white/15 bg-white/[0.08] text-zinc-200">
          <BadgeCheck size={27} strokeWidth={1.7} aria-hidden="true" />
        </div>
      </div>
    </GlassCard>
  );
}
