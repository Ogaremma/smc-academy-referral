import { ExternalLink } from 'lucide-react';
import { openExternalUrl } from '@/lib/telegram';
import { GlassCard } from './GlassCard';

export function RegistrationFormCard({ url }: { url: string }) {
  return (
    <GlassCard className="p-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="eyebrow">Registration</p>
          <h2 className="mt-1 text-base font-semibold text-white">Complete your application</h2>
        </div>
        <button
          type="button"
          className="primary-button shrink-0"
          onClick={() => openExternalUrl(url)}
          aria-label="Open SMC Academy registration form"
        >
          <ExternalLink size={17} /> Open form
        </button>
      </div>
    </GlassCard>
  );
}
