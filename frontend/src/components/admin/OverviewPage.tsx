import type { AdminAffiliate, AdminAuditLog, AdminReferral } from '@/types/api';
import { AdminDataTable } from '@/components/admin/AdminDataTable';
import { AdminEmptyState } from '@/components/admin/AdminStates';
import { AdminKpi } from '@/components/admin/AdminKpi';
import { IdentityCell, adminIdentity } from '@/components/admin/IdentityCell';
import { StatusBadge } from '@/components/admin/StatusBadge';
import { candidateIdentity, formatDate, formatDateTime } from '@/components/admin/format';

interface OverviewPageProps {
  affiliates: AdminAffiliate[];
  referrals: AdminReferral[];
  auditLogs: AdminAuditLog[];
}

export function OverviewPage({ affiliates, referrals, auditLogs }: OverviewPageProps) {
  const activeCount = affiliates.filter((affiliate) => affiliate.account_status === 'ACTIVE').length;
  const revokedCount = affiliates.filter((affiliate) => affiliate.account_status === 'REVOKED').length;
  const verifiedReferralCount = referrals.filter((referral) => referral.status === 'verified').length;
  const recentReferrals = referrals.slice(0, 5);
  const recentActivity = auditLogs.slice(0, 5);

  return (
    <section className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <AdminKpi label="Current affiliates" value={affiliates.length} description="Active and revoked accounts with links" />
        <AdminKpi label="Active" value={activeCount} description="Eligible for broadcasts" />
        <AdminKpi label="Revoked" value={revokedCount} description="Available for restore" />
        <AdminKpi label="Verified referrals" value={verifiedReferralCount} description="All recorded lifecycles" />
      </div>

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-semibold">Recent referrals</h2>
          <span className="text-xs text-zinc-500">Latest {recentReferrals.length}</span>
        </div>
        {recentReferrals.length === 0 ? (
          <AdminEmptyState title="No referrals yet" description="Verified form submissions will appear here." />
        ) : (
          <AdminDataTable
            rows={recentReferrals}
            getKey={(referral) => referral.id}
            emptyTitle="No referrals yet"
            emptyMessage="Verified form submissions will appear here."
            columns={[
              {
                key: 'affiliate',
                header: 'Affiliate',
                render: (referral) => <IdentityCell user={referral.referrer} />,
              },
              {
                key: 'candidate',
                header: 'Candidate',
                render: (referral) => <span className="font-medium">{candidateIdentity(referral)}</span>,
              },
              {
                key: 'status',
                header: 'Status',
                render: (referral) => <StatusBadge status={referral.status} />,
              },
              {
                key: 'date',
                header: 'Date',
                render: (referral) => <span className="text-zinc-400">{formatDate(referral.created_at)}</span>,
              },
            ]}
          />
        )}
      </div>

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-semibold">Recent admin activity</h2>
          <span className="text-xs text-zinc-500">Latest {recentActivity.length}</span>
        </div>
        {recentActivity.length === 0 ? (
          <AdminEmptyState title="No admin activity yet" description="State-changing actions will appear here." />
        ) : (
          <AdminDataTable
            rows={recentActivity}
            getKey={(log) => log.id}
            emptyTitle="No admin activity yet"
            emptyMessage="State-changing actions will appear here."
            columns={[
              {
                key: 'action',
                header: 'Action',
                render: (log) => <span className="font-medium">{log.action.replace(/_/g, ' ')}</span>,
              },
              {
                key: 'actor',
                header: 'Actor',
                render: (log) => <span>{adminIdentity(log.actor)}</span>,
              },
              {
                key: 'target',
                header: 'Target',
                render: (log) => <span>{log.target ? adminIdentity(log.target) : '—'}</span>,
              },
              {
                key: 'timestamp',
                header: 'Timestamp',
                render: (log) => <span className="text-zinc-400">{formatDateTime(log.created_at)}</span>,
              },
            ]}
          />
        )}
      </div>
    </section>
  );
}
