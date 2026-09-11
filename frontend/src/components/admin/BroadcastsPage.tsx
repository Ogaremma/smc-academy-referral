import { useState } from 'react';
import { Radio, Send } from 'lucide-react';
import type { AdminBroadcast } from '@/types/api';
import { AdminDataTable } from '@/components/admin/AdminDataTable';
import { IdentityCell } from '@/components/admin/IdentityCell';
import { StatusBadge } from '@/components/admin/StatusBadge';
import { formatDateTime } from '@/components/admin/format';

interface BroadcastsPageProps {
  broadcasts: AdminBroadcast[];
  eligibleCount: number;
  sending: boolean;
  onSend: (message: string) => Promise<boolean>;
}

export function BroadcastsPage({
  broadcasts,
  eligibleCount,
  sending,
  onSend,
}: BroadcastsPageProps) {
  const [message, setMessage] = useState('');

  const submit = () => {
    if (!message.trim() || sending) return;
    if (!window.confirm(`Send this broadcast to ${eligibleCount} eligible affiliate${eligibleCount === 1 ? '' : 's'}?`)) return;
    void (async () => {
      const sent = await onSend(message);
      if (sent) setMessage('');
    })();
  };

  return (
    <section className="space-y-5">
      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/[0.06]">
            <Radio size={18} />
          </span>
          <div>
            <h2 className="font-semibold">Compose broadcast</h2>
            <p className="mt-1 text-sm text-zinc-500">
              {eligibleCount} eligible affiliate{eligibleCount === 1 ? '' : 's'} with active accounts and referral links
            </p>
          </div>
        </div>

        <label className="mt-5 block">
          <span className="text-xs font-medium uppercase tracking-[.14em] text-zinc-500">Message</span>
          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            maxLength={4096}
            placeholder="Write an update for eligible affiliates"
            className="mt-2 min-h-36 w-full rounded-lg border border-white/10 bg-white/[0.04] p-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-teal-300/40 focus:outline-none"
          />
        </label>

        <div className="mt-4 rounded-lg border border-white/10 bg-black/30 p-4">
          <p className="text-xs font-medium uppercase tracking-[.14em] text-zinc-500">Preview</p>
          <p className="mt-2 whitespace-pre-wrap text-sm text-zinc-200">
            {message || 'Your broadcast preview appears here.'}
          </p>
        </div>

        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-zinc-500">{message.length}/4096 characters</p>
          <button type="button" className="primary-button sm:w-40" disabled={sending || !message.trim()} onClick={submit}>
            <Send size={16} />
            {sending ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>

      <div>
        <h2 className="mb-3 font-semibold">Broadcast history</h2>
        <AdminDataTable
          rows={broadcasts}
          getKey={(broadcast) => broadcast.id}
          emptyTitle="No broadcasts yet"
          emptyMessage="Sent broadcasts and delivery results will appear here."
          columns={[
            {
              key: 'message',
              header: 'Message',
              render: (broadcast) => <p className="max-w-[320px] truncate text-zinc-200">{broadcast.message}</p>,
            },
            {
              key: 'actor',
              header: 'Sent by',
              render: (broadcast) => <IdentityCell user={broadcast.actor} />,
            },
            {
              key: 'recipients',
              header: 'Recipients',
              render: (broadcast) => <span className="tabular-nums">{broadcast.target_count}</span>,
            },
            {
              key: 'delivery',
              header: 'Delivery',
              render: (broadcast) => (
                <span className="text-zinc-400">
                  {broadcast.success_count} delivered · {broadcast.failed_count} failed
                </span>
              ),
            },
            {
              key: 'status',
              header: 'Status',
              render: (broadcast) => <StatusBadge status={broadcast.status} />,
            },
            {
              key: 'created_at',
              header: 'Created',
              render: (broadcast) => <span className="text-zinc-400">{formatDateTime(broadcast.created_at)}</span>,
            },
          ]}
        />
      </div>
    </section>
  );
}
