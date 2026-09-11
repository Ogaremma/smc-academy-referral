import { useMemo, useState } from 'react';
import { Search, ShieldCheck, UserPlus } from 'lucide-react';
import type { AdminAffiliate, AdminUser } from '@/types/api';
import { AdminDataTable, type SortDirection } from '@/components/admin/AdminDataTable';
import { IdentityCell, adminIdentity } from '@/components/admin/IdentityCell';
import { StatusBadge } from '@/components/admin/StatusBadge';
import { formatDate } from '@/components/admin/format';

interface AdministratorsPageProps {
  administrators: AdminUser[];
  affiliates: AdminAffiliate[];
  pending: boolean;
  onAdd: (affiliateId: number) => void;
  onRemove: (administrator: AdminUser) => void;
  onDemote: (administrator: AdminUser) => void;
}

export function AdministratorsPage({
  administrators,
  affiliates,
  pending,
  onAdd,
  onRemove,
  onDemote,
}: AdministratorsPageProps) {
  const [query, setQuery] = useState('');
  const [selectedAffiliateId, setSelectedAffiliateId] = useState('');
  const [sortKey, setSortKey] = useState('administrator');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');

  const candidates = useMemo(
    () => affiliates.filter((affiliate) => !affiliate.is_admin),
    [affiliates],
  );

  const filteredAdministrators = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return administrators;
    return administrators.filter((administrator) =>
      [administrator.username, administrator.first_name, administrator.last_name, String(administrator.telegram_id)]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
        .includes(normalizedQuery),
    );
  }, [administrators, query]);

  const sortedAdministrators = useMemo(() => {
    const value = (administrator: AdminUser): string | number => {
      if (sortKey === 'status') return administrator.account_status;
      if (sortKey === 'role') return administrator.is_protected_admin ? 0 : 1;
      if (sortKey === 'created_at') return Date.parse(administrator.created_at);
      return adminIdentity(administrator).toLowerCase();
    };

    return [...filteredAdministrators].sort((left, right) => {
      const leftValue = value(left);
      const rightValue = value(right);
      if (leftValue === rightValue) return 0;
      const comparison = leftValue > rightValue ? 1 : -1;
      return sortDirection === 'asc' ? comparison : -comparison;
    });
  }, [filteredAdministrators, sortDirection, sortKey]);

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
      <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/[0.06]">
            <UserPlus size={18} />
          </span>
          <div className="min-w-0 flex-1">
            <h2 className="font-semibold">Add administrator</h2>
            <p className="mt-1 text-sm text-zinc-500">Promote a current affiliate with an active referral link.</p>
          </div>
        </div>
        <div className="mt-4 flex flex-col gap-3 sm:flex-row">
          <select
            value={selectedAffiliateId}
            onChange={(event) => setSelectedAffiliateId(event.target.value)}
            className="min-h-11 flex-1 rounded-lg border border-white/10 bg-[#111318] px-3 text-sm text-zinc-200 focus:border-teal-300/40 focus:outline-none"
            aria-label="Select an affiliate to promote"
          >
            <option value="">Select an affiliate</option>
            {candidates.map((affiliate) => (
              <option key={affiliate.id} value={affiliate.id}>
                {adminIdentity(affiliate)}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="primary-button sm:w-40"
            disabled={pending || !selectedAffiliateId}
            onClick={() => {
              const affiliateId = Number(selectedAffiliateId);
              if (affiliateId) onAdd(affiliateId);
            }}
          >
            {pending ? 'Adding...' : 'Add admin'}
          </button>
        </div>
      </div>

      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" size={16} />
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search administrators"
          className="min-h-11 w-full rounded-lg border border-white/10 bg-white/[0.04] pl-10 pr-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-teal-300/40 focus:outline-none"
        />
      </div>

      <AdminDataTable
        rows={sortedAdministrators}
        getKey={(administrator) => administrator.id}
        sortKey={sortKey}
        sortDirection={sortDirection}
        onSort={toggleSort}
        emptyTitle="No administrators found"
        emptyMessage="Add a trusted affiliate to help manage the program."
        columns={[
          {
            key: 'administrator',
            header: 'Administrator',
            sortValue: (administrator) => adminIdentity(administrator).toLowerCase(),
            render: (administrator) => <IdentityCell user={administrator} />,
          },
          {
            key: 'status',
            header: 'Status',
            sortValue: (administrator) => administrator.account_status,
            render: (administrator) => <StatusBadge status={administrator.account_status} />,
          },
          {
            key: 'role',
            header: 'Role',
            sortValue: (administrator) => (administrator.is_protected_admin ? 0 : 1),
            render: (administrator) =>
              administrator.is_protected_admin ? (
                <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-400/30 bg-amber-400/10 px-2.5 py-1 text-[11px] font-semibold text-amber-300">
                  <ShieldCheck size={12} />
                  Protected
                </span>
              ) : (
                <span className="text-zinc-400">Standard</span>
              ),
          },
          {
            key: 'created_at',
            header: 'Added',
            sortValue: (administrator) => Date.parse(administrator.created_at),
            render: (administrator) => <span className="text-zinc-400">{formatDate(administrator.created_at)}</span>,
          },
          {
            key: 'actions',
            header: 'Actions',
            render: (administrator) =>
              administrator.is_protected_admin ? (
                <span className="text-xs text-zinc-500">Protected administrator</span>
              ) : (
                <div className="flex flex-wrap gap-2">
                  <button type="button" disabled={pending} className="rounded-md border border-rose-400/30 bg-rose-400/10 px-3 py-2 text-xs font-semibold text-rose-200 transition hover:bg-rose-400/20 disabled:opacity-50" onClick={() => onRemove(administrator)}>
                    Remove
                  </button>
                  <button type="button" disabled={pending} className="rounded-md border border-white/10 px-3 py-2 text-xs font-medium text-zinc-200 transition hover:bg-white/[0.08] disabled:opacity-50" onClick={() => onDemote(administrator)}>
                    Demote
                  </button>
                </div>
              ),
          },
        ]}
      />
    </section>
  );
}
