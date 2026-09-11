const statusStyles: Record<string, string> = {
  ACTIVE: 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300',
  REVOKED: 'border-amber-400/30 bg-amber-400/10 text-amber-300',
  verified: 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300',
  pending: 'border-sky-400/30 bg-sky-400/10 text-sky-300',
  rejected: 'border-rose-400/30 bg-rose-400/10 text-rose-300',
  QUEUED: 'border-sky-400/30 bg-sky-400/10 text-sky-300',
  SENDING: 'border-sky-400/30 bg-sky-400/10 text-sky-300',
  COMPLETED: 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300',
  PARTIAL: 'border-amber-400/30 bg-amber-400/10 text-amber-300',
  FAILED: 'border-rose-400/30 bg-rose-400/10 text-rose-300',
};

export function StatusBadge({ status }: { status: string }) {
  const style = statusStyles[status] ?? 'border-white/10 bg-white/[0.06] text-zinc-300';
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide ${style}`}>
      {status}
    </span>
  );
}
