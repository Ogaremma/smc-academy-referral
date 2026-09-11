import { useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import type { AdminAffiliate } from '@/types/api';
import { AdminDataTable, type SortDirection } from '@/components/admin/AdminDataTable';
import { IdentityCell, adminIdentity } from '@/components/admin/IdentityCell';
import { StatusBadge } from '@/components/admin/StatusBadge';
import { formatDate } from '@/components/admin/format';

interface AffiliatesPageProps {
  affiliates: AdminAffiliate[];
  pending: boolean;
  onSelect: (affiliate: AdminAffiliate) => void;
  onRevoke: (affiliate: AdminAffiliate) => void;
  onRestore: (affiliate: AdminAffiliate) => void;
}

export function AffiliatesPage({
  affiliates,
  pending,
  onSelect,
  onRevoke,
  onRestore,
}: AffiliatesPageProps) {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState<'ALL' | 'ACTIVE' | 'REVOKED'>('ALL');
  const [sortKey, setSortKey] = useState('created_at');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const filteredAffiliates = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return affiliates.filter((affiliate) => {
      const matchesStatus = status === 'ALL' || affiliate.account_status === status;
      const searchable = [
        affiliate.username,
        affiliate.first_name,
        affiliate.last_name,
        String(affiliate.telegram_id),
        affiliate.referral_code,
        affiliate.account_status,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return matchesStatus && (!normalizedQuery || searchable.includes(normalizedQuery));
    });
  }, [affiliates, query, status]);

  const sortedAffiliates = useMemo(() => {
    const value = (affiliate: AdminAffiliate): string | number => {
      if (sortKey === 'affiliate') return adminIdentity(affiliate).toLowerCase();
      if (sortKey === 'status') return affiliate.account_status;
      if (sortKey === 'code') return affiliate.referral_code;
      if (sortKey === 'referrals') return affiliate.referral_count;
      return Date.parse(affiliate.created_at);
    };

    return [...filteredAffiliates].sort((left, right) => {
      const leftValue = value(left);
      const rightValue = value(right);
      if (leftValue === rightValue) return 0;
      const comparison = leftValue > rightValue ? 1 : -1;
      return sortDirection === 'asc' ? comparison : -comparison;
    });
  }, [filteredAffiliates, sortDirection, sortKey]);

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
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <label className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" size={16} />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search name, username, Telegram ID, or code"
            className="min-h-11 w-full rounded-lg border border-white/10 bg-white/[0.04] pl-10 pr-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-teal-300/40 focus:outline-none"
          />
        </label>
        <select
          value={status}
          onChange={(event) => setStatus(event.target.value as 'ALL' | 'ACTIVE' | 'REVOKED')}
          className="min-h-11 rounded-lg border border-white/10 bg-[#111318] px-3 text-sm text-zinc-200 focus:border-teal-300/40 focus:outline-none"
          aria-label="Filter affiliates by status"
        >
          <option value="ALL">All statuses</option>
          <option value="ACTIVE">Active</option>
          <option value="REVOKED">Revoked</option>
        </select>
      </div>

      <AdminDataTable
        rows={sortedAffiliates}
        getKey={(affiliate) => affiliate.id}
        sortKey={sortKey}
        sortDirection={sortDirection}
        onSort={toggleSort}
        emptyTitle="No affiliates found"
        emptyMessage="Adjust your search or status filter to find an affiliate."
        columns={[
          {
            key: 'affiliate',
            header: 'Affiliate',
            sortValue: (affiliate) => adminIdentity(affiliate).toLowerCase(),
            render: (affiliate) => <IdentityCell user={affiliate} />,
          },
          {
            key: 'status',
            header: 'Status',
            sortValue: (affiliate) => affiliate.account_status,
            render: (affiliate) => <StatusBadge status={affiliate.account_status} />,
          },
          {
            key: 'code',
            header: 'Referral code',
            sortValue: (affiliate) => affiliate.referral_code,
            render: (affiliate) => <span className="font-mono text-xs text-zinc-300">{affiliate.referral_code}</span>,
          },
          {
            key: 'referrals',
            header: 'Referrals',
            sortValue: (affiliate) => affiliate.referral_count,
            render: (affiliate) => <span className="tabular-nums">{affiliate.referral_count}</span>,
          },
          {
            key: 'created_at',
            header: 'Joined',
            sortValue: (affiliate) => Date.parse(affiliate.created_at),
            render: (affiliate) => <span className="text-zinc-400">{formatDate(affiliate.created_at)}</span>,
          },
          {
            key: 'actions',
            header: 'Actions',
            render: (affiliate) => (
              <div className="flex flex-wrap items-center gap-2">
                <button type="button" className="rounded-md border border-white/10 px-3 py-2 text-xs font-medium text-zinc-200 transition hover:bg-white/[0.08]" onClick={() => onSelect(affiliate)}>
                  View
                </button>
                {affiliate.account_status === 'REVOKED' ? (
                  <button type="button" disabled={pending} className="rounded-md bg-white px-3 py-2 text-xs font-semibold text-black transition hover:bg-zinc-200 disabled:opacity-50" onClick={() => onRestore(affiliate)}>
                    Restore
                  </button>
                ) : (
                  <button type="button" disabled={pending} className="rounded-md border border-rose-400/30 bg-rose-400/10 px-3 py-2 text-xs font-semibold text-rose-200 transition hover:bg-rose-400/20 disabled:opacity-50" onClick={() => onRevoke(affiliate)}>
                    Revoke
                  </button>
                )}
              </div>
            ),
          },
        ]}
      />
    </section>
  );
}
