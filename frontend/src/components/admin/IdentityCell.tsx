import type { AdminUserSummary } from '@/types/api';

export function adminDisplayName(user: AdminUserSummary): string {
  return [user.first_name, user.last_name]
    .map((part) => part?.trim())
    .filter(Boolean)
    .join(' ');
}

export function adminIdentity(user: AdminUserSummary): string {
  const username = user.username?.trim();
  if (username) return username.startsWith('@') ? username : `@${username}`;

  const displayName = adminDisplayName(user);
  if (displayName) return displayName;

  return `Telegram ${user.telegram_id}`;
}

/**
 * Secondary line for the identity cell: the part of the Telegram profile that
 * the primary identity does not already show. It never repeats the identity and
 * never falls back to the numeric Telegram id, which is only displayed as the
 * identity itself when no username and no name exist.
 */
export function adminSecondaryIdentity(user: AdminUserSummary): string {
  const username = user.username?.trim();
  const displayName = adminDisplayName(user);
  return username && displayName ? displayName : '';
}

export function IdentityCell({ user }: { user: AdminUserSummary }) {
  const primary = adminIdentity(user);
  const secondary = adminSecondaryIdentity(user);
  const initial = primary.replace('@', '').charAt(0).toUpperCase();

  return (
    <div className="flex min-w-0 items-center gap-3">
      {user.photo_url ? (
        <img src={user.photo_url} alt="" className="h-9 w-9 shrink-0 rounded-full border border-white/10 object-cover" />
      ) : (
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/[0.08] text-xs font-semibold">
          {initial}
        </span>
      )}
      <span className="min-w-0">
        <span className="block truncate font-medium text-zinc-100">{primary}</span>
        {secondary && <span className="block truncate text-xs text-zinc-500">{secondary}</span>}
      </span>
    </div>
  );
}
