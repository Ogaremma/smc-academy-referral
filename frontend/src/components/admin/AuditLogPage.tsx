import { useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import type { AdminAuditLog } from '@/types/api';
import { AdminDataTable, type SortDirection } from '@/components/admin/AdminDataTable';
import { IdentityCell, adminIdentity } from '@/components/admin/IdentityCell';
import { formatDateTime } from '@/components/admin/format';

export function AuditLogPage({ auditLogs }: { auditLogs: AdminAuditLog[] }) {
  const [query, setQuery] = useState('');
  const [sortKey, setSortKey] = useState('created_at');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const filteredLogs = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return auditLogs;
    return auditLogs.filter((log) =>
      [
        log.action,
        adminIdentity(log.actor),
        log.target ? adminIdentity(log.target) : '',
      ]
        .join(' ')
        .toLowerCase()
        .includes(normalizedQuery),
    );
  }, [auditLogs, query]);

  const sortedLogs = useMemo(() => {
    const value = (log: AdminAuditLog): string | number => {
      if (sortKey === 'action') return log.action;
      if (sortKey === 'actor') return adminIdentity(log.actor).toLowerCase();
      if (sortKey === 'target') return log.target ? adminIdentity(log.target).toLowerCase() : '';
      return Date.parse(log.created_at);
    };

    return [...filteredLogs].sort((left, right) => {
      const leftValue = value(left);
      const rightValue = value(right);
      if (leftValue === rightValue) return 0;
      const comparison = leftValue > rightValue ? 1 : -1;
      return sortDirection === 'asc' ? comparison : -comparison;
    });
  }, [filteredLogs, sortDirection, sortKey]);

  const toggleSort = (key: string) => {
    if (key === sortKey) {
      setSortDirection((direction) => (direction === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setSortKey(key);
    setSortDirection('asc');
  };

  return (
    <section className="space-y-4">
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" size={16} />
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search action, actor, or target"
          className="min-h-11 w-full rounded-lg border border-white/10 bg-white/[0.04] pl-10 pr-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-teal-300/40 focus:outline-none"
        />
      </div>

      <AdminDataTable
        rows={sortedLogs}
        getKey={(log) => log.id}
        sortKey={sortKey}
        sortDirection={sortDirection}
        onSort={toggleSort}
        emptyTitle="No admin activity found"
        emptyMessage="State-changing admin actions will appear here."
        columns={[
          {
            key: 'action',
            header: 'Action',
            sortValue: (log) => log.action,
            render: (log) => <span className="font-medium">{log.action.replace(/_/g, ' ')}</span>,
          },
          {
            key: 'actor',
            header: 'Actor',
            sortValue: (log) => adminIdentity(log.actor).toLowerCase(),
            render: (log) => <IdentityCell user={log.actor} />,
          },
          {
            key: 'target',
            header: 'Target',
            sortValue: (log) => (log.target ? adminIdentity(log.target).toLowerCase() : ''),
            render: (log) => (log.target ? <IdentityCell user={log.target} /> : <span className="text-zinc-500">—</span>),
          },
          {
            key: 'created_at',
            header: 'Timestamp',
            sortValue: (log) => Date.parse(log.created_at),
            render: (log) => <span className="text-zinc-400">{formatDateTime(log.created_at)}</span>,
          },
        ]}
      />
    </section>
  );
}
