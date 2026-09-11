import { AlertTriangle, Inbox } from 'lucide-react';

export function AdminLoading({ label }: { label: string }) {
  return (
    <div className="space-y-4" aria-label={`Loading ${label}`} role="status">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((index) => (
          <div key={index} className="h-28 animate-pulse rounded-xl border border-white/10 bg-white/[0.05]" />
        ))}
      </div>
      <div className="h-72 animate-pulse rounded-xl border border-white/10 bg-white/[0.05]" />
    </div>
  );
}

export function AdminError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="rounded-xl border border-rose-400/20 bg-rose-400/[0.07] p-6">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 shrink-0 text-rose-300" size={20} />
        <div>
          <p className="font-medium text-rose-100">Unable to load {message}</p>
          <p className="mt-1 text-sm text-rose-200/70">Check your connection and try again.</p>
        </div>
      </div>
      <button type="button" className="primary-button mt-5" onClick={onRetry}>
        Retry
      </button>
    </div>
  );
}

export function AdminEmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-xl border border-dashed border-white/12 bg-white/[0.02] p-10 text-center">
      <Inbox className="mx-auto text-zinc-500" size={24} />
      <p className="mt-3 font-medium text-zinc-200">{title}</p>
      <p className="mt-1 text-sm text-zinc-500">{description}</p>
    </div>
  );
}
