import { useState } from 'react';
import { ExternalLink } from 'lucide-react';
import { openExternalUrl } from '@/lib/telegram';
import type { SubmissionField } from '@/types/api';

/** Build a directly previewable image URL for common Google Drive / image links. */
export function proofPreviewUrl(value: string): string | null {
  const driveFile = value.match(/drive\.google\.com\/file\/d\/([^/?#]+)/);
  if (driveFile) return `https://drive.google.com/thumbnail?id=${driveFile[1]}&sz=w600`;
  const driveOpen = value.match(/drive\.google\.com\/(?:open|uc)\?[^#]*?\bid=([^&#]+)/);
  if (driveOpen) return `https://drive.google.com/thumbnail?id=${driveOpen[1]}&sz=w600`;
  if (/\.(png|jpe?g|gif|webp|bmp)(\?|#|$)/i.test(value)) return value;
  return null;
}

export function ProofPreview({ url, label = 'Open payment proof' }: { url: string; label?: string }) {
  const [failed, setFailed] = useState(false);
  const image = proofPreviewUrl(url);

  return (
    <div className="mt-2 space-y-2">
      {image && !failed && (
        <img
          src={image}
          alt="Payment proof submitted with this referral"
          className="max-h-44 w-auto rounded-lg border border-white/10 object-contain"
          onError={() => setFailed(true)}
        />
      )}
      <button
        type="button"
        className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-xs font-medium text-zinc-100 transition hover:bg-white/[0.08]"
        onClick={() => openExternalUrl(url)}
      >
        <ExternalLink size={14} /> {label}
      </button>
    </div>
  );
}

export function SubmissionFieldValue({
  field,
  proofLabel,
}: {
  field: SubmissionField;
  proofLabel?: string;
}) {
  if (field.is_link) {
    if (field.category === 'payment') return <ProofPreview url={field.value} label={proofLabel} />;
    return (
      <button
        type="button"
        className="break-all text-left text-sm font-medium text-teal-200 underline-offset-2 hover:underline"
        onClick={() => openExternalUrl(field.value)}
      >
        {field.value}
      </button>
    );
  }
  return <p className="break-words text-sm font-medium text-zinc-100">{field.value}</p>;
}

export interface SubmissionSection {
  key: string;
  title: string;
  fields: SubmissionField[];
}

const SECTION_TITLES: { key: string; title: string }[] = [
  { key: 'registration', title: 'Registration information' },
  { key: 'payment', title: 'Payment information' },
  { key: 'other', title: 'Other information' },
];

/**
 * Group stored answers into stable sections. Fields are rendered from whatever
 * the backend stored, so new Google Form questions are never silently dropped:
 * unknown categories fall through to "Other information".
 */
export function groupSubmissionFields(fields: SubmissionField[]): SubmissionSection[] {
  return SECTION_TITLES.map((section) => ({
    ...section,
    fields:
      section.key === 'other'
        ? fields.filter(
            (field) => field.category !== 'registration' && field.category !== 'payment',
          )
        : fields.filter((field) => field.category === section.key),
  })).filter((section) => section.fields.length > 0);
}
