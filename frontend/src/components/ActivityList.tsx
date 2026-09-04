import { Inbox, ShieldCheck } from 'lucide-react';
import type { ReferralActivity } from '@/types/api';
import { GlassCard } from './GlassCard';

function formatDate(value: string | null): string {
  if (!value) return 'Recently verified';
  return new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(value));
}

export function ActivityList({ items }: { items: ReferralActivity[] }) {
  return (
    <section className="mt-8" aria-labelledby="activity-heading">
      <p className="eyebrow">Latest updates</p>
      <h2 id="activity-heading" className="section-title">Recent activity</h2>
      {items.length === 0 ? (
        <GlassCard className="mt-3 flex flex-col items-center px-6 py-9 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-white/10 bg-white/[0.05] text-zinc-400"><Inbox size={22} /></div>
          <p className="mt-4 text-sm font-medium text-zinc-200">No verified activity yet</p>
          <p className="mt-1 max-w-xs text-xs leading-5 text-zinc-500">Verified registrations will appear here after a referred student submits the official form.</p>
        </GlassCard>
      ) : (
        <GlassCard className="mt-3 overflow-hidden">
          <ul className="divide-y divide-white/[0.07]">
            {items.map((item) => <li key={item.id} className="flex items-center gap-3 px-4 py-4"><div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-white/[0.08] text-zinc-200"><ShieldCheck size={17} /></div><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium text-zinc-200">Private registration</p><p className="mt-0.5 text-xs text-zinc-500">Verified registration</p></div><time className="shrink-0 text-[11px] text-zinc-500" dateTime={item.verified_at ?? undefined}>{formatDate(item.verified_at)}</time></li>)}
          </ul>
        </GlassCard>
      )}
    </section>
  );
}
