import type { AdminUserSummary } from '@/types/api';

export function adminIdentity(user: AdminUserSummary): string {
  const username = user.username?.trim();
  if (username) return username.startsWith('@') ? username : `@${username}`;

  const displayName = [user.first_name, user.last_name]
    .map((part) => part?.trim())
    .filter(Boolean)
    .join(' ');
  if (displayName) return displayName;

  return `Telegram ${user.telegram_id}`;
}

export function adminSecondaryIdentity(user: AdminUserSummary): string {
  const displayName = [user.first_name, user.last_name]
    .map((part) => part?.trim())
    .filter(Boolean)
    .join(' ');

  if (user.username?.trim() && displayName) return displayName;
  if (!user.username?.trim() && displayName) return `Telegram ${user.telegram_id}`;
  return 'Telegram profile';
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
        <span className="block truncate text-xs text-zinc-500">{secondary}</span>
      </span>
    </div>
  );
}
