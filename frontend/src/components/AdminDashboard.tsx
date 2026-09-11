import { useCallback, useEffect, useState } from 'react';
import {
  adminAdd,
  adminAdministrators,
  adminAffiliates,
  adminAuditLogs,
  adminBroadcasts,
  adminCreateBroadcast,
  adminDemote,
  adminReferrals,
  adminRemove,
  adminRestore,
  adminRevoke,
} from '@/lib/api';
import type {
  AdminAffiliate,
  AdminAuditLog,
  AdminBroadcast,
  AdminReferral,
  AdminUser,
  AdminUserSummary,
} from '@/types/api';
import { AdminError, AdminLoading } from '@/components/admin/AdminStates';
import { AdminShell, type AdminSection } from '@/components/admin/AdminShell';
import { AffiliateDetailPage } from '@/components/admin/AffiliateDetailPage';
import { AffiliatesPage } from '@/components/admin/AffiliatesPage';
import { AdministratorsPage } from '@/components/admin/AdministratorsPage';
import { AuditLogPage } from '@/components/admin/AuditLogPage';
import { BroadcastsPage } from '@/components/admin/BroadcastsPage';
import { OverviewPage } from '@/components/admin/OverviewPage';
import { ReferralsPage } from '@/components/admin/ReferralsPage';

interface AdminData {
  affiliates: AdminAffiliate[];
  referrals: AdminReferral[];
  administrators: AdminUser[];
  auditLogs: AdminAuditLog[];
  broadcasts: AdminBroadcast[];
}

const emptyAdminData: AdminData = {
  affiliates: [],
  referrals: [],
  administrators: [],
  auditLogs: [],
  broadcasts: [],
};

const sectionLabels: Record<AdminSection, string> = {
  overview: 'overview',
  affiliates: 'affiliates',
  referrals: 'referrals',
  broadcasts: 'broadcasts',
  administrators: 'administrators',
  'audit-log': 'audit log',
};

interface AdminDashboardProps {
  admin: AdminUserSummary;
  onBack: () => void;
}

export function AdminDashboard({ admin, onBack }: AdminDashboardProps) {
  const [section, setSection] = useState<AdminSection>('overview');
  const [data, setData] = useState<AdminData>(emptyAdminData);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionPending, setActionPending] = useState(false);
  const [actionError, setActionError] = useState('');
  const [actionNotice, setActionNotice] = useState('');
  const [selectedAffiliateId, setSelectedAffiliateId] = useState<number | null>(null);

  const loadSection = useCallback(async (target: AdminSection) => {
    setLoading(true);
    setError('');
    try {
      if (target === 'overview') {
        const [affiliates, referrals, auditLogs] = await Promise.all([
          adminAffiliates(),
          adminReferrals(),
          adminAuditLogs(),
        ]);
        setData((current) => ({ ...current, affiliates, referrals, auditLogs }));
      } else if (target === 'affiliates') {
        const affiliates = await adminAffiliates();
        setData((current) => ({ ...current, affiliates }));
      } else if (target === 'referrals') {
        const referrals = await adminReferrals();
        setData((current) => ({ ...current, referrals }));
      } else if (target === 'broadcasts') {
        const [broadcasts, affiliates] = await Promise.all([
          adminBroadcasts(),
          adminAffiliates(),
        ]);
        setData((current) => ({ ...current, broadcasts, affiliates }));
      } else if (target === 'administrators') {
        const [administrators, affiliates] = await Promise.all([
          adminAdministrators(),
          adminAffiliates(),
        ]);
        setData((current) => ({ ...current, administrators, affiliates }));
      } else {
        const auditLogs = await adminAuditLogs();
        setData((current) => ({ ...current, auditLogs }));
      }
    } catch {
      setError(sectionLabels[target]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (section !== 'affiliates') setSelectedAffiliateId(null);
    void loadSection(section);
  }, [loadSection, section]);

  const runAction = async (action: () => Promise<unknown>, notice: string): Promise<boolean> => {
    if (actionPending) return false;
    setActionPending(true);
    setActionError('');
    setActionNotice('');
    try {
      await action();
      setActionNotice(notice);
      await loadSection(section);
      return true;
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : 'The action could not be completed.');
      return false;
    } finally {
      setActionPending(false);
    }
  };

  const revokeAffiliate = (affiliate: AdminAffiliate) => {
    if (!window.confirm(`Revoke ${affiliate.username ? `@${affiliate.username}` : 'this affiliate'}? They cannot create a new affiliate lifecycle until restored.`)) return;
    void runAction(() => adminRevoke(affiliate.id), 'Affiliate revoked.');
  };

  const restoreAffiliate = (affiliate: AdminAffiliate) => {
    if (!window.confirm(`Restore ${affiliate.username ? `@${affiliate.username}` : 'this affiliate'} to their existing lifecycle?`)) return;
    void runAction(() => adminRestore(affiliate.id), 'Affiliate restored.');
  };

  const addAdministrator = (affiliateId: number) => {
    void runAction(() => adminAdd(affiliateId), 'Administrator added.');
  };

  const removeAdministrator = (administrator: AdminUser) => {
    if (!window.confirm('Remove this administrator? They will keep their affiliate account.')) return;
    void runAction(() => adminRemove(administrator.id), 'Administrator removed.');
  };

  const demoteAdministrator = (administrator: AdminUser) => {
    if (!window.confirm('Demote this administrator? They will keep their affiliate account.')) return;
    void runAction(() => adminDemote(administrator.id), 'Administrator demoted.');
  };

  const sendBroadcast = async (message: string) => {
    return runAction(() => adminCreateBroadcast(message), 'Broadcast queued for delivery.');
  };

  const actionBanner = actionError || actionNotice;

  return (
    <AdminShell
      activeSection={section}
      onSectionChange={setSection}
      onExit={onBack}
      admin={admin}
    >
      {actionBanner && (
        <div
          role={actionError ? 'alert' : 'status'}
          className={`mb-4 rounded-lg border px-4 py-3 text-sm ${
            actionError
              ? 'border-rose-400/25 bg-rose-400/10 text-rose-200'
              : 'border-emerald-400/25 bg-emerald-400/10 text-emerald-200'
          }`}
        >
          {actionBanner}
        </div>
      )}

      {section === 'affiliates' && selectedAffiliateId !== null ? (
        <AffiliateDetailPage
          affiliateId={selectedAffiliateId}
          onBack={() => setSelectedAffiliateId(null)}
          onChanged={async () => {
            await loadSection('affiliates');
          }}
        />
      ) : loading ? (
        <AdminLoading label={sectionLabels[section]} />
      ) : error ? (
        <AdminError message={error} onRetry={() => void loadSection(section)} />
      ) : section === 'overview' ? (
        <OverviewPage
          affiliates={data.affiliates}
          referrals={data.referrals}
          auditLogs={data.auditLogs}
        />
      ) : section === 'affiliates' ? (
        <AffiliatesPage
          affiliates={data.affiliates}
          pending={actionPending}
          onSelect={(affiliate) => setSelectedAffiliateId(affiliate.id)}
          onRevoke={revokeAffiliate}
          onRestore={restoreAffiliate}
        />
      ) : section === 'referrals' ? (
        <ReferralsPage referrals={data.referrals} />
      ) : section === 'broadcasts' ? (
        <BroadcastsPage
          broadcasts={data.broadcasts}
          eligibleCount={data.affiliates.filter((affiliate) => affiliate.account_status === 'ACTIVE').length}
          sending={actionPending}
          onSend={sendBroadcast}
        />
      ) : section === 'administrators' ? (
        <AdministratorsPage
          administrators={data.administrators}
          affiliates={data.affiliates}
          pending={actionPending}
          onAdd={addAdministrator}
          onRemove={removeAdministrator}
          onDemote={demoteAdministrator}
        />
      ) : (
        <AuditLogPage auditLogs={data.auditLogs} />
      )}
    </AdminShell>
  );
}
