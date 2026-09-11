import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const api = vi.hoisted(() => ({
  ApiError: class ApiError extends Error {
    constructor(
      public readonly status: number,
      message: string,
    ) {
      super(message);
      this.name = 'ApiError';
    }
  },
  adminAdd: vi.fn(),
  adminAdministrators: vi.fn(),
  adminAffiliate: vi.fn(),
  adminAffiliates: vi.fn(),
  adminAuditLogs: vi.fn(),
  adminBroadcasts: vi.fn(),
  adminCreateBroadcast: vi.fn(),
  adminDemote: vi.fn(),
  adminPayout: vi.fn(),
  adminReferral: vi.fn(),
  adminReferrals: vi.fn(),
  adminRemove: vi.fn(),
  adminRestore: vi.fn(),
  adminRevoke: vi.fn(),
}));

vi.mock('@/lib/api', () => api);

import { AdminDashboard } from '@/components/AdminDashboard';

const admin = {
  id: 99,
  telegram_id: 999,
  username: 'admin',
  first_name: 'Ada',
  last_name: 'Admin',
  photo_url: null,
};

const alice = {
  id: 1,
  telegram_id: 101,
  username: 'alice',
  first_name: 'Alice',
  last_name: 'Affiliate',
  photo_url: null,
  account_status: 'ACTIVE',
  is_admin: false,
  is_protected_admin: false,
  created_at: '2026-09-01T10:00:00Z',
  referral_code: 'SMC-ALICE',
  referral_count: 2,
};

const bob = {
  id: 2,
  telegram_id: 102,
  username: null,
  first_name: 'Bob',
  last_name: 'Builder',
  photo_url: null,
  account_status: 'REVOKED',
  is_admin: false,
  is_protected_admin: false,
  created_at: '2026-09-02T10:00:00Z',
  referral_code: 'SMC-BOB',
  referral_count: 0,
};

const unnamed = {
  id: 3,
  telegram_id: 103,
  username: null,
  first_name: null,
  last_name: null,
  photo_url: null,
  account_status: 'ACTIVE',
  is_admin: false,
  is_protected_admin: false,
  created_at: '2026-09-03T10:00:00Z',
  referral_code: 'SMC-UNNAMED',
  referral_count: 0,
};

const affiliates = [alice, bob, unnamed];
const referrals = [
  {
    id: 9,
    referrer: { id: 1, telegram_id: 101, username: 'alice', first_name: 'Alice', last_name: 'Affiliate', photo_url: null },
    candidate_email: 'candidate@example.com',
    candidate_telegram_handle: '@candidate',
    status: 'verified',
    created_at: '2026-09-04T10:00:00Z',
  },
];
const administrators = [
  { ...alice, id: 3, telegram_id: 103, username: 'Web3Launcherr', first_name: 'Web3', last_name: 'Launcher', is_admin: true, is_protected_admin: true },
  { ...bob, id: 4, telegram_id: 104, username: 'operator', first_name: 'Operator', last_name: 'User', is_admin: true, is_protected_admin: false },
];
const auditLogs = [
  {
    id: 1,
    action: 'affiliate_revoked',
    actor: admin,
    target: bob,
    metadata_json: '{}',
    created_at: '2026-09-05T10:00:00Z',
  },
];
const broadcasts = [
  {
    id: 1,
    actor: admin,
    message: 'Welcome back',
    status: 'COMPLETED',
    target_count: 2,
    success_count: 2,
    failed_count: 0,
    created_at: '2026-09-06T10:00:00Z',
    completed_at: '2026-09-06T10:01:00Z',
  },
];

const renderDashboard = () => render(<AdminDashboard admin={admin} onBack={vi.fn()} />);

describe('AdminDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.adminAffiliates.mockResolvedValue(affiliates);
    api.adminReferrals.mockResolvedValue(referrals);
    api.adminAdministrators.mockResolvedValue(administrators);
    api.adminAuditLogs.mockResolvedValue(auditLogs);
    api.adminBroadcasts.mockResolvedValue(broadcasts);
    api.adminAffiliate.mockResolvedValue({ ...alice, is_active: true });
    api.adminPayout.mockResolvedValue({
      id: 1,
      user_id: 1,
      account_name: 'Alice Affiliate',
      bank_name: 'Example Bank',
      account_number: '0123456789',
      created_at: '2026-09-01T11:00:00Z',
      updated_at: '2026-09-01T11:00:00Z',
    });
    api.adminReferral.mockResolvedValue(referrals[0]);
  });

  it('renders overview KPIs, recent referrals, and admin activity', async () => {
    renderDashboard();

    expect(await screen.findByText('Current affiliates')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('Verified referrals')).toBeInTheDocument();
    expect(screen.getByText('Recent referrals')).toBeInTheDocument();
    expect(screen.getByText('Recent admin activity')).toBeInTheDocument();
    expect(screen.getByText('@candidate')).toBeInTheDocument();
    expect(screen.getByText('affiliate revoked')).toBeInTheDocument();
  });

  it('uses sidebar navigation and Management grouping', async () => {
    renderDashboard();
    expect(await screen.findByRole('button', { name: 'Overview' })).toBeInTheDocument();
    expect(screen.getByText('Operations')).toBeInTheDocument();
    expect(screen.getByText('Management')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Audit Log' }));
    expect(await screen.findByText('Timestamp')).toBeInTheDocument();
  });

  it('renders current affiliates with readable identities and no database ID labels', async () => {
    renderDashboard();
    fireEvent.click(screen.getByRole('button', { name: 'Affiliates' }));

    expect(await screen.findByText('@alice')).toBeInTheDocument();
    expect(screen.getByText('Bob Builder')).toBeInTheDocument();
    expect(screen.getByText('Telegram 103')).toBeInTheDocument();
    expect(screen.getByText('SMC-ALICE')).toBeInTheDocument();
    expect(screen.queryByText('#1')).not.toBeInTheDocument();
    expect(screen.queryByText('#2')).not.toBeInTheDocument();
    expect(screen.queryByText('#3')).not.toBeInTheDocument();
  });

  it('searches and filters affiliates', async () => {
    renderDashboard();
    fireEvent.click(screen.getByRole('button', { name: 'Affiliates' }));
    await screen.findByText('@alice');

    fireEvent.change(screen.getByPlaceholderText('Search name, username, Telegram ID, or code'), {
      target: { value: 'alice' },
    });
    expect(screen.getByText('@alice')).toBeInTheDocument();
    expect(screen.queryByText('Bob Builder')).not.toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText('Search name, username, Telegram ID, or code'), {
      target: { value: '' },
    });
    fireEvent.change(screen.getByLabelText('Filter affiliates by status'), {
      target: { value: 'REVOKED' },
    });
    expect(screen.getByText('Bob Builder')).toBeInTheDocument();
    expect(screen.queryByText('@alice')).not.toBeInTheDocument();
  });

  it('opens affiliate detail with lifecycle-scoped referrals and payout details', async () => {
    api.adminReferrals.mockResolvedValue([]);
    renderDashboard();
    fireEvent.click(screen.getByRole('button', { name: 'Affiliates' }));
    const aliceRow = (await screen.findByText('@alice')).closest('tr')!;
    fireEvent.click(within(aliceRow).getByRole('button', { name: 'View' }));

    expect(await screen.findByText('Referral code')).toBeInTheDocument();
    expect(screen.getByText('SMC-ALICE')).toBeInTheDocument();
    expect(screen.getByText('No referrals in this lifecycle')).toBeInTheDocument();
    expect(api.adminAffiliate).toHaveBeenCalledWith(1);
    expect(api.adminReferrals).toHaveBeenCalledWith(1);

    fireEvent.click(screen.getByRole('button', { name: 'Payout details' }));
    expect(await screen.findByText('Example Bank')).toBeInTheDocument();
    expect(screen.getByText('0123456789')).toBeInTheDocument();
  });

  it('shows the payout empty state for a 404 response', async () => {
    api.adminPayout.mockRejectedValueOnce(new api.ApiError(404, 'Payout details not found'));
    renderDashboard();
    fireEvent.click(screen.getByRole('button', { name: 'Affiliates' }));
    const aliceRow = (await screen.findByText('@alice')).closest('tr')!;
    fireEvent.click(within(aliceRow).getByRole('button', { name: 'View' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Payout details' }));

    expect(await screen.findByText('No payout details have been saved for this affiliate.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument();
  });

  it('shows a retryable payout error for non-404 failures', async () => {
    api.adminPayout
      .mockRejectedValueOnce(new api.ApiError(403, 'Administrator access required'))
      .mockResolvedValueOnce({
        id: 1,
        user_id: 1,
        account_name: 'Alice Affiliate',
        bank_name: 'Example Bank',
        account_number: '0123456789',
        created_at: '2026-09-01T11:00:00Z',
        updated_at: '2026-09-01T11:00:00Z',
      });
    renderDashboard();
    fireEvent.click(screen.getByRole('button', { name: 'Affiliates' }));
    const aliceRow = (await screen.findByText('@alice')).closest('tr')!;
    fireEvent.click(within(aliceRow).getByRole('button', { name: 'View' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Payout details' }));

    expect(await screen.findByText('You do not have permission to view these payout details.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByText('Example Bank')).toBeInTheDocument();
    expect(api.adminPayout).toHaveBeenCalledTimes(2);
  });

  it('revokes and restores affiliates while preventing duplicate submissions', async () => {
    api.adminRevoke.mockResolvedValue({ status: 'REVOKED' });
    api.adminRestore.mockResolvedValue({ status: 'ACTIVE' });
    renderDashboard();
    fireEvent.click(screen.getByRole('button', { name: 'Affiliates' }));
    const aliceRow = (await screen.findByText('@alice')).closest('tr')!;
    const revokeButton = within(aliceRow).getByRole('button', { name: 'Revoke' });
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true);

    fireEvent.click(revokeButton);
    fireEvent.click(revokeButton);
    expect(api.adminRevoke).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(screen.getByText('Affiliate revoked.')).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText('Filter affiliates by status'), {
      target: { value: 'REVOKED' },
    });
    const bobRow = screen.getByText('Bob Builder').closest('tr')!;
    fireEvent.click(within(bobRow).getByRole('button', { name: 'Restore' }));
    expect(api.adminRestore).toHaveBeenCalledWith(2);
    await waitFor(() => expect(screen.getByText('Affiliate restored.')).toBeInTheDocument());
    confirm.mockRestore();
  });

  it('shows protected administrators without destructive controls', async () => {
    renderDashboard();
    fireEvent.click(screen.getByRole('button', { name: 'Administrators' }));

    const protectedRow = (await screen.findByText('@Web3Launcherr')).closest('tr')!;
    expect(within(protectedRow).getByText('Protected')).toBeInTheDocument();
    expect(protectedRow.querySelectorAll('button')).toHaveLength(0);
    expect(screen.getByText('Protected administrator')).toBeInTheDocument();
  });

  it('renders referral records and safe detail fields', async () => {
    renderDashboard();
    fireEvent.click(screen.getByRole('button', { name: 'Referrals' }));

    expect(await screen.findByText('@candidate')).toBeInTheDocument();
    expect(screen.getByText('@alice')).toBeInTheDocument();
    expect(screen.getByText('verified')).toBeInTheDocument();
    expect(screen.queryByText('#9')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'View' }));
    expect(await screen.findByText('Candidate Telegram')).toBeInTheDocument();
    expect(screen.getByText('candidate@example.com')).toBeInTheDocument();
  });

  it('composes and queues a broadcast with eligible recipient count', async () => {
    api.adminCreateBroadcast.mockResolvedValue(broadcasts[0]);
    renderDashboard();
    fireEvent.click(screen.getByRole('button', { name: 'Broadcasts' }));

    expect(await screen.findByText('2 eligible affiliates with active accounts and referral links')).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText('Write an update for eligible affiliates'), {
      target: { value: 'Cohort update' },
    });
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true);
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));

    expect(api.adminCreateBroadcast).toHaveBeenCalledWith('Cohort update');
    await waitFor(() => expect(screen.getByText('Broadcast queued for delivery.')).toBeInTheDocument());
    expect(screen.getByPlaceholderText('Write an update for eligible affiliates')).toHaveValue('');
    confirm.mockRestore();
  });
});
