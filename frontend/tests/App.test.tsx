import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const api = vi.hoisted(() => ({
  ApiError: class ApiError extends Error {
    constructor(public readonly status: number, message: string) {
      super(message);
      this.name = 'ApiError';
    }
  },
  deleteAccount: vi.fn(),
  getReferrals: vi.fn(),
  getReferral: vi.fn(),
  getPayout: vi.fn(),
  savePayout: vi.fn(),
}));
vi.mock('@/lib/api', () => api);
vi.mock('@/lib/telegram', () => ({ setTelegramBackButton: vi.fn(() => () => {}) }));
vi.mock('@/hooks/useDashboard', () => ({
  useDashboard: () => ({
    state: {
      status: 'ready',
      data: {
        profile: { user: { telegram_id: 1, first_name: 'Ada', photo_url: null }, referral_code: 'SMC-ABC' },
        dashboard: {
          total_verified_referrals: 2,
          pending_referrals: 0,
          personal_referral_link: 'https://example.test/r',
          registration_form_url: null,
          recent_verified_activity: [],
        },
      },
    },
    retry: vi.fn(),
    register: vi.fn(),
  }),
}));

import App from '@/App';

const referrals = [
  {
    id: 7,
    name: 'John Doe',
    email: 'john@example.com',
    telegram: '@johndoe',
    course: 'Frontend Development',
    status: 'verified',
    created_at: '2026-01-01T00:00:00Z',
    registered_at: '2026-01-01T00:00:00Z',
    verified_at: '2026-01-02T00:00:00Z',
  },
];

beforeEach(() => {
  vi.clearAllMocks();
  api.getReferrals.mockResolvedValue({ total: 1, registered: 1, referrals });
  api.getPayout.mockRejectedValue(new api.ApiError(404, 'Payout details not found'));
});

describe('dashboard', () => {
  it('renders the active dashboard controls', () => {
    render(<App />);
    expect(screen.getByText('View All Referrals')).toBeInTheDocument();
    expect(screen.getByText('Payout Details')).toBeInTheDocument();
    expect(screen.getByText('Delete Account')).toBeInTheDocument();
  });

  it('orders link before code and opens My Referrals', async () => {
    render(<App />);
    const link = screen.getByText('Personal link');
    const code = screen.getByText('Referral code');
    expect(link.compareDocumentPosition(code) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    fireEvent.click(screen.getByText('View All Referrals'));
    expect(await screen.findByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('Frontend Development')).toBeInTheDocument();
    expect(screen.getByText('verified')).toBeInTheDocument();
  });
});

describe('referral states', () => {
  it('shows list loading then success', async () => {
    let resolve!: (value: unknown) => void;
    api.getReferrals.mockReturnValue(new Promise((r) => { resolve = r; }));
    render(<App />);
    fireEvent.click(screen.getByText('View All Referrals'));
    expect(screen.getByLabelText('Loading referrals')).toBeInTheDocument();
    resolve({ total: 1, registered: 1, referrals });
    expect(await screen.findByText('John Doe')).toBeInTheDocument();
  });

  it('shows list error and retries to empty state', async () => {
    api.getReferrals.mockRejectedValueOnce(new Error('fail')).mockResolvedValueOnce({ total: 0, registered: 0, referrals: [] });
    render(<App />);
    fireEvent.click(screen.getByText('View All Referrals'));
    expect(await screen.findByText('Unable to load your referrals.')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Retry'));
    expect(await screen.findByText('No Referrals Yet')).toBeInTheDocument();
    expect(screen.getByText(/start building your network/i)).toBeInTheDocument();
    expect(api.getReferrals).toHaveBeenCalledTimes(2);
  });

  it('shows detail loading, the complete submission, and back navigation', async () => {
    let resolve!: (value: unknown) => void;
    api.getReferral.mockReturnValue(new Promise((r) => { resolve = r; }));
    render(<App />);
    fireEvent.click(screen.getByText('View All Referrals'));
    fireEvent.click(await screen.findByLabelText('Open referral John Doe'));
    expect(screen.getByLabelText('Loading referral details')).toBeInTheDocument();

    resolve({
      ...referrals[0],
      form_fields: [
        { label: 'Full Name', value: 'John Doe', category: 'registration', is_link: false },
        { label: 'Phone Number', value: '08012345678', category: 'registration', is_link: false },
        { label: 'Email Address', value: 'john@example.com', category: 'registration', is_link: false },
        { label: 'Class Preference', value: 'Online', category: 'registration', is_link: false },
        { label: 'Payment Reference', value: 'TRX-1', category: 'payment', is_link: false },
        { label: 'Payment Screenshot', value: 'https://drive.google.com/file/d/abc123/view', category: 'payment', is_link: true },
        { label: 'How did you hear about us?', value: 'A friend', category: 'other', is_link: false },
      ],
    });

    expect(await screen.findByText('08012345678')).toBeInTheDocument();
    expect(screen.getByText('Phone Number')).toBeInTheDocument();
    // Every submitted answer, including payment information, is visible.
    expect(screen.getByText('Registration information')).toBeInTheDocument();
    expect(screen.getByText('Payment information')).toBeInTheDocument();
    expect(screen.getByText('Other information')).toBeInTheDocument();
    expect(screen.getByText('TRX-1')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Open payment proof/ })).toBeInTheDocument();
    expect(screen.getByText('A friend')).toBeInTheDocument();
    expect(screen.queryByText('response_id')).not.toBeInTheDocument();
    expect(screen.queryByText('referral_code')).not.toBeInTheDocument();

    fireEvent.click(screen.getByLabelText('Back'));
    expect(screen.getByText('My Referrals')).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('Back'));
    expect(screen.getByText('View All Referrals')).toBeInTheDocument();
  });

  it('shows detail error with usable Back', async () => {
    api.getReferral.mockRejectedValue(new Error('fail'));
    render(<App />);
    fireEvent.click(screen.getByText('View All Referrals'));
    fireEvent.click(await screen.findByLabelText('Open referral John Doe'));
    expect(await screen.findByText('Unable to load referral details.')).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('Back'));
    expect(screen.getByText('My Referrals')).toBeInTheDocument();
  });
});

describe('payout details', () => {
  it('creates payout details when none exist', async () => {
    api.savePayout.mockResolvedValue({
      account_name: 'Ada Lovelace',
      bank_name: 'Access Bank',
      account_number: '0123456789',
      updated_at: '2026-01-01T00:00:00Z',
    });
    render(<App />);
    fireEvent.click(screen.getByText('Payout Details'));

    expect(await screen.findByText(/No payout details yet/i)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Account name'), { target: { value: 'Ada Lovelace' } });
    fireEvent.change(screen.getByLabelText('Account number'), { target: { value: '0123456789' } });
    fireEvent.change(screen.getByLabelText('Bank name'), { target: { value: 'Access Bank' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save payout details' }));

    expect(api.savePayout).toHaveBeenCalledWith({ account_name: 'Ada Lovelace', bank_name: 'Access Bank', account_number: '0123456789' });
    expect(await screen.findByText('Payout details saved.')).toBeInTheDocument();
    expect(screen.getByText('Saved account')).toBeInTheDocument();
  });

  it('loads and edits existing payout details', async () => {
    api.getPayout.mockResolvedValue({
      account_name: 'Ada',
      bank_name: 'GTBank',
      account_number: '1111',
      updated_at: '2026-01-01T00:00:00Z',
    });
    api.savePayout.mockResolvedValue({
      account_name: 'Ada',
      bank_name: 'GTBank',
      account_number: '2222',
      updated_at: '2026-02-01T00:00:00Z',
    });
    render(<App />);
    fireEvent.click(screen.getByText('Payout Details'));

    expect(await screen.findByText('1111')).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('Edit payout details'));
    fireEvent.change(screen.getByLabelText('Account number'), { target: { value: '2222' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save payout details' }));

    expect(await screen.findByText('2222')).toBeInTheDocument();
  });

  it('shows a retryable error when payout details cannot load', async () => {
    api.getPayout
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValueOnce({
        account_name: 'Ada',
        bank_name: 'GTBank',
        account_number: '1111',
        updated_at: '2026-01-01T00:00:00Z',
      });
    render(<App />);
    fireEvent.click(screen.getByText('Payout Details'));

    expect(await screen.findByText('Unable to load your payout details.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Retry/ }));
    expect(await screen.findByText('1111')).toBeInTheDocument();
  });
});

describe('delete states', () => {
  it('cancel closes without deleting', () => {
    render(<App />);
    fireEvent.click(screen.getByText('Delete Account'));
    expect(screen.getByText('Delete Affiliate Account?')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Cancel'));
    expect(api.deleteAccount).not.toHaveBeenCalled();
  });

  it('prevents duplicates and renders successful deletion', async () => {
    let resolve!: () => void;
    api.deleteAccount.mockReturnValue(new Promise<void>((r) => { resolve = r; }));
    render(<App />);
    fireEvent.click(screen.getByText('Delete Account'));
    const confirm = screen.getAllByRole('button', { name: 'Delete Account' }).at(-1)!;
    fireEvent.click(confirm);
    expect(screen.getByText('Deleting...')).toBeDisabled();
    fireEvent.click(screen.getByText('Deleting...'));
    expect(api.deleteAccount).toHaveBeenCalledTimes(1);
    resolve();
    expect(await screen.findByText('Account Deleted')).toBeInTheDocument();
    expect(screen.queryByText('View All Referrals')).not.toBeInTheDocument();
  });

  it('shows failure and permits retry', async () => {
    api.deleteAccount.mockRejectedValueOnce(new Error('Unable to delete')).mockResolvedValueOnce(undefined);
    render(<App />);
    fireEvent.click(screen.getByText('Delete Account'));
    fireEvent.click(screen.getAllByRole('button', { name: 'Delete Account' }).at(-1)!);
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole('button', { name: 'Delete Account' }).at(-1)!);
    expect(await screen.findByText('Account Deleted')).toBeInTheDocument();
    expect(api.deleteAccount).toHaveBeenCalledTimes(2);
  });
});
