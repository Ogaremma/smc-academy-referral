import { useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import type { AdminReferral } from '@/types/api';
import { AdminDataTable, type SortDirection } from '@/components/admin/AdminDataTable';
import { IdentityCell, adminIdentity } from '@/components/admin/IdentityCell';
import { ReferralDetailPanel } from '@/components/admin/ReferralDetailPanel';
import { StatusBadge } from '@/components/admin/StatusBadge';
import { candidateIdentity, formatDate } from '@/components/admin/format';

export function ReferralsPage({ referrals }: { referrals: AdminReferral[] }) {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState<'ALL' | 'verified' | 'pending' | 'rejected'>('ALL');
  const [sortKey, setSortKey] = useState('created_at');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [selectedReferralId, setSelectedReferralId] = useState<number | null>(null);

  const filteredReferrals = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return referrals.filter((referral) => {
      const matchesStatus = status === 'ALL' || referral.status === status;
      const searchable = [
        adminIdentity(referral.referrer),
        referral.candidate_telegram_handle,
        referral.candidate_email,
        referral.referral_code,
        referral.status,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return matchesStatus && (!normalizedQuery || searchable.includes(normalizedQuery));
    });
  }, [query, referrals, status]);

  const sortedReferrals = useMemo(() => {
    const value = (referral: AdminReferral): string | number => {
      if (sortKey === 'affiliate') return adminIdentity(referral.referrer).toLowerCase();
      if (sortKey === 'candidate') return candidateIdentity(referral).toLowerCase();
      if (sortKey === 'status') return referral.status;
      return Date.parse(referral.created_at);
    };

    return [...filteredReferrals].sort((left, right) => {
      const leftValue = value(left);
      const rightValue = value(right);
      if (leftValue === rightValue) return 0;
      const comparison = leftValue > rightValue ? 1 : -1;
      return sortDirection === 'asc' ? comparison : -comparison;
    });
  }, [filteredReferrals, sortDirection, sortKey]);

  const toggleSort = (key: string) => {
    if (key === sortKey) {
      setSortDirection((direction) => (direction === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setSortKey(key);
    setSortDirection('asc');
  };

  if (selectedReferralId !== null) {
    return (
      <ReferralDetailPanel
        referralId={selectedReferralId}
        onBack={() => setSelectedReferralId(null)}
      />
    );
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <label className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" size={16} />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search affiliate or candidate"
            className="min-h-11 w-full rounded-lg border border-white/10 bg-white/[0.04] pl-10 pr-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-teal-300/40 focus:outline-none"
          />
        </label>
        <select
          value={status}
          onChange={(event) => setStatus(event.target.value as 'ALL' | 'verified' | 'pending' | 'rejected')}
          className="min-h-11 rounded-lg border border-white/10 bg-[#111318] px-3 text-sm text-zinc-200 focus:border-teal-300/40 focus:outline-none"
          aria-label="Filter referrals by status"
        >
          <option value="ALL">All statuses</option>
          <option value="verified">Verified</option>
          <option value="pending">Pending</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>

      <AdminDataTable
        rows={sortedReferrals}
        getKey={(referral) => referral.id}
        sortKey={sortKey}
        sortDirection={sortDirection}
        onSort={toggleSort}
        emptyTitle="No referrals found"
        emptyMessage="Referrals appear here after verified form submissions."
        columns={[
          {
            key: 'affiliate',
            header: 'Affiliate',
            sortValue: (referral) => adminIdentity(referral.referrer).toLowerCase(),
            render: (referral) => <IdentityCell user={referral.referrer} />,
          },
          {
            key: 'candidate',
            header: 'Candidate',
            sortValue: (referral) => candidateIdentity(referral).toLowerCase(),
            render: (referral) => (
              <div className="min-w-0">
                <p className="truncate font-medium">{candidateIdentity(referral)}</p>
                {referral.candidate_email && (
                  <p className="truncate text-xs text-zinc-500">{referral.candidate_email}</p>
                )}
              </div>
            ),
          },
          {
            key: 'status',
            header: 'Status',
            sortValue: (referral) => referral.status,
            render: (referral) => <StatusBadge status={referral.status} />,
          },
          {
            key: 'created_at',
            header: 'Date',
            sortValue: (referral) => Date.parse(referral.created_at),
            render: (referral) => <span className="text-zinc-400">{formatDate(referral.created_at)}</span>,
          },
          {
            key: 'actions',
            header: 'Actions',
            render: (referral) => (
              <button
                type="button"
                className="rounded-md border border-white/10 px-3 py-2 text-xs font-medium text-zinc-200 transition hover:bg-white/[0.08]"
                onClick={() => setSelectedReferralId(referral.id)}
              >
                View
              </button>
            ),
          },
        ]}
      />
    </section>
  );
}
