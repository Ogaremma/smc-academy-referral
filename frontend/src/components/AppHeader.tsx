interface AppHeaderProps { firstName: string | null; photoUrl: string | null; }

export function AppHeader({ firstName, photoUrl }: AppHeaderProps) {
  const greeting = firstName?.trim() ? `Welcome back, ${firstName.trim()}` : 'Welcome back';

  return (
    <header className="flex items-center justify-between gap-4 pt-2">
      <div className="min-w-0">
        <div className="mb-4 flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-md border border-emerald-200/20 bg-emerald-300 text-xs font-black text-emerald-950">SMC</div>
          <div>
            <p className="text-sm font-semibold leading-none text-white">SMC Academy</p>
            <p className="mt-1 text-[10px] uppercase tracking-[.16em] text-zinc-500">Referral portal</p>
          </div>
        </div>
        <h1 className="truncate text-2xl font-semibold text-white">{greeting}</h1>
        <p className="mt-1.5 text-sm text-zinc-400">Here is the impact you have made.</p>
      </div>
      <div className="h-12 w-12 shrink-0 overflow-hidden rounded-lg border border-white/10 bg-white/[0.06] p-0.5">
        {photoUrl ? <img src={photoUrl} alt="Telegram profile" className="h-full w-full rounded-[6px] object-cover" /> : <div className="flex h-full w-full items-center justify-center rounded-[6px] bg-emerald-300/10 text-sm font-semibold text-emerald-200">{firstName?.[0]?.toUpperCase() ?? 'S'}</div>}
      </div>
    </header>
  );
}
