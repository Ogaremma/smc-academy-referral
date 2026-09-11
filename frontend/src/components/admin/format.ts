export function formatDate(value: string | null): string {
  if (!value) return '—';
  return new Date(value).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function formatDateTime(value: string | null): string {
  if (!value) return '—';
  return new Date(value).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export function candidateIdentity(referral: {
  candidate_telegram_handle: string | null;
  candidate_email: string | null;
}): string {
  return referral.candidate_telegram_handle?.trim() || referral.candidate_email?.trim() || 'Candidate';
}
