import { describe, expect, it } from 'vitest';
import {
  adminIdentity,
  adminSecondaryIdentity,
} from '@/components/admin/IdentityCell';
import { candidateIdentity } from '@/components/admin/format';

const base = {
  id: 17,
  telegram_id: 6261204018,
  username: null,
  first_name: null,
  last_name: null,
  photo_url: null,
};

describe('adminIdentity', () => {
  it('shows @username when a Telegram username exists', () => {
    expect(
      adminIdentity({ ...base, username: 'Web3Launcherr', first_name: 'Ogar', last_name: 'Emma' }),
    ).toBe('@Web3Launcherr');
  });

  it('keeps a username that already carries the @ prefix', () => {
    expect(adminIdentity({ ...base, username: '@Web3Launcherr' })).toBe('@Web3Launcherr');
  });

  it('falls back to the full Telegram name', () => {
    expect(adminIdentity({ ...base, first_name: 'Ogar', last_name: 'Emma' })).toBe('Ogar Emma');
  });

  it('falls back to the first name alone', () => {
    expect(adminIdentity({ ...base, first_name: 'Ogar' })).toBe('Ogar');
  });

  it('shows the numeric Telegram id only when no profile data exists', () => {
    expect(adminIdentity(base)).toBe('Telegram 6261204018');
  });

  it('ignores blank profile values', () => {
    expect(adminIdentity({ ...base, username: '   ', first_name: '', last_name: '  ' })).toBe(
      'Telegram 6261204018',
    );
  });

  it('never renders the internal database id as the identity', () => {
    expect(adminIdentity(base)).not.toContain('17');
    expect(adminIdentity(base)).toBe(`Telegram ${base.telegram_id}`);
  });
});

describe('adminSecondaryIdentity', () => {
  it('shows the display name under a username', () => {
    expect(
      adminSecondaryIdentity({ ...base, username: 'Web3Launcherr', first_name: 'Ogar', last_name: 'Emma' }),
    ).toBe('Ogar Emma');
  });

  it('never repeats the identity or the numeric id', () => {
    expect(adminSecondaryIdentity({ ...base, first_name: 'Ogar', last_name: 'Emma' })).toBe('');
    expect(adminSecondaryIdentity(base)).toBe('');
    expect(adminSecondaryIdentity({ ...base, username: 'Web3Launcherr' })).toBe('');
  });
});

describe('candidateIdentity', () => {
  it('prefers the Telegram handle, then the email, then a neutral label', () => {
    expect(candidateIdentity({ candidate_telegram_handle: '@adebello', candidate_email: 'a@b.c' })).toBe('@adebello');
    expect(candidateIdentity({ candidate_telegram_handle: null, candidate_email: 'a@b.c' })).toBe('a@b.c');
    expect(candidateIdentity({ candidate_telegram_handle: '  ', candidate_email: null })).toBe('Candidate');
  });
});
