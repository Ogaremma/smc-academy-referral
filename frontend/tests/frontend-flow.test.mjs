import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const app = await readFile(new URL('../src/App.tsx', import.meta.url), 'utf8');
const api = await readFile(new URL('../src/lib/api.ts', import.meta.url), 'utf8');

test('dashboard copy and referral ordering are present', () => {
  assert.match(app, /Sign Up As an SMC Academy Affiliate/);
  assert.match(app, /View All Referrals/);
  assert.ok(app.lastIndexOf('<ReferralLinkCard') < app.lastIndexOf('<ReferralCodeCard'));
});

test('delete flow is authenticated, bounded, and does not reload', () => {
  assert.match(api, /method: 'DELETE'/);
  assert.match(api, /authenticatedHeaders\(\)/);
  assert.doesNotMatch(app, /window\.location\.reload/);
  assert.match(app, /Deleting\.\.\./);
  assert.match(app, /disabled=\{deleting === 'busy'\}/);
});

test('delete success clears session and renders an account-deleted state', () => {
  assert.match(api, /sessionToken\.clear\(\)/);
  assert.match(app, /Account Deleted/);
});
