import type { ReactNode } from 'react';
import { useState } from 'react';
import {
  ArrowLeft,
  ClipboardList,
  LayoutDashboard,
  Menu,
  Radio,
  ScrollText,
  ShieldCheck,
  Users,
  X,
} from 'lucide-react';
import type { AdminUserSummary } from '@/types/api';
import { adminIdentity, adminSecondaryIdentity } from '@/components/admin/IdentityCell';

export type AdminSection =
  | 'overview'
  | 'affiliates'
  | 'referrals'
  | 'broadcasts'
  | 'administrators'
  | 'audit-log';

const navigationItems: Array<{
  section: AdminSection;
  label: string;
  icon: typeof Users;
  group: 'Operations' | 'Management';
}> = [
  { section: 'overview', label: 'Overview', icon: LayoutDashboard, group: 'Operations' },
  { section: 'affiliates', label: 'Affiliates', icon: Users, group: 'Operations' },
  { section: 'referrals', label: 'Referrals', icon: ClipboardList, group: 'Operations' },
  { section: 'broadcasts', label: 'Broadcasts', icon: Radio, group: 'Operations' },
  { section: 'administrators', label: 'Administrators', icon: ShieldCheck, group: 'Management' },
  { section: 'audit-log', label: 'Audit Log', icon: ScrollText, group: 'Management' },
];

const sectionLabels: Record<AdminSection, string> = {
  overview: 'Overview',
  affiliates: 'Affiliates',
  referrals: 'Referrals',
  broadcasts: 'Broadcasts',
  administrators: 'Administrators',
  'audit-log': 'Audit Log',
};

interface AdminShellProps {
  activeSection: AdminSection;
  onSectionChange: (section: AdminSection) => void;
  onExit: () => void;
  admin: AdminUserSummary;
  children: ReactNode;
}

export function AdminShell({
  activeSection,
  onSectionChange,
  onExit,
  admin,
  children,
}: AdminShellProps) {
  const [drawerOpen, setDrawerOpen] = useState(false);

  const selectSection = (section: AdminSection) => {
    onSectionChange(section);
    setDrawerOpen(false);
  };

  const navigation = () => (
    <nav className="space-y-1" aria-label="Admin navigation">
      {(['Operations', 'Management'] as const).map((group) => (
        <div key={group} className="mt-6 first:mt-0">
          <p className="px-3 text-[11px] font-semibold uppercase tracking-[.16em] text-zinc-600">{group}</p>
          <div className="mt-2 space-y-1">
            {navigationItems
              .filter((item) => item.group === group)
              .map(({ section, label, icon: Icon }) => {
                const active = section === activeSection;
                return (
                  <button
                    key={section}
                    type="button"
                    onClick={() => selectSection(section)}
                    aria-current={active ? 'page' : undefined}
                    className={`flex min-h-11 w-full items-center gap-3 rounded-lg px-3 text-sm font-medium transition ${
                      active
                        ? 'bg-white text-black shadow-[0_10px_30px_rgba(255,255,255,0.10)]'
                        : 'text-zinc-400 hover:bg-white/[0.07] hover:text-white'
                    }`}
                  >
                    <Icon size={17} className="shrink-0" />
                    {label}
                  </button>
                );
              })}
          </div>
        </div>
      ))}
    </nav>
  );

  const adminFooter = (
    <div className="mt-auto border-t border-white/10 pt-4">
      <div className="flex items-center gap-3">
        {admin.photo_url ? (
          <img src={admin.photo_url} alt="" className="h-10 w-10 rounded-full border border-white/10 object-cover" />
        ) : (
          <span className="flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/[0.08] text-sm font-semibold">
            {adminIdentity(admin).replace('@', '').charAt(0).toUpperCase()}
          </span>
        )}
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">{adminIdentity(admin)}</p>
          <p className="truncate text-xs text-zinc-500">{adminSecondaryIdentity(admin)}</p>
        </div>
      </div>
      <button
        type="button"
        onClick={onExit}
        className="mt-4 flex min-h-11 w-full items-center gap-2 rounded-lg border border-white/10 px-3 text-sm text-zinc-300 transition hover:bg-white/[0.07] hover:text-white"
      >
        <ArrowLeft size={16} />
        Affiliate dashboard
      </button>
    </div>
  );

  return (
    <div className="app-shell min-h-screen text-zinc-100">
      <div className="mx-auto flex w-full max-w-7xl">
        <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-white/10 bg-[#0a0b0f]/95 px-4 py-6 md:flex">
          <div>
            <p className="text-sm font-semibold tracking-tight">SMC Academy</p>
            <p className="mt-1 text-xs text-zinc-500">Affiliate operations</p>
          </div>
          {navigation()}
          {adminFooter}
        </aside>

        <div className="min-w-0 flex-1">
          <header className="sticky top-0 z-30 border-b border-white/10 bg-[#07090d]/95 px-4 pt-safe backdrop-blur md:px-8">
            <div className="flex min-h-16 items-center justify-between gap-3 py-3">
              <div className="flex min-w-0 items-center gap-3">
                <button
                  type="button"
                  className="icon-button md:hidden"
                  onClick={() => setDrawerOpen(true)}
                  aria-label="Open admin navigation"
                >
                  <Menu size={18} />
                </button>
                <div className="min-w-0">
                  <p className="truncate text-[11px] font-semibold uppercase tracking-[.16em] text-zinc-500">Admin workspace</p>
                  <h1 className="truncate text-lg font-semibold">{sectionLabels[activeSection]}</h1>
                </div>
              </div>
              <button type="button" className="icon-button md:hidden" onClick={onExit} aria-label="Return to affiliate dashboard">
                <ArrowLeft size={18} />
              </button>
            </div>
          </header>

          <main className="px-4 pb-safe pt-5 md:px-8 md:pb-10">
            {children}
          </main>
        </div>
      </div>

      {drawerOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-black/70"
            onClick={() => setDrawerOpen(false)}
            aria-label="Close admin navigation"
          />
          <div className="absolute inset-y-0 left-0 flex w-[82vw] max-w-xs flex-col border-r border-white/10 bg-[#0a0b0f] px-4 pb-safe pt-safe">
            <div className="flex items-center justify-between py-4">
              <div>
                <p className="text-sm font-semibold">SMC Academy</p>
                <p className="mt-1 text-xs text-zinc-500">Affiliate operations</p>
              </div>
              <button type="button" className="icon-button" onClick={() => setDrawerOpen(false)} aria-label="Close navigation">
                <X size={18} />
              </button>
            </div>
            {navigation()}
            {adminFooter}
          </div>
        </div>
      )}
    </div>
  );
}
