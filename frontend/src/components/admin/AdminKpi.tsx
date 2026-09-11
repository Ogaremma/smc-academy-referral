export function AdminKpi({
  label,
  value,
  description,
}: {
  label: string;
  value: string | number;
  description?: string;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.035] p-5">
      <p className="text-xs font-medium uppercase tracking-[.14em] text-zinc-500">{label}</p>
      <p className="mt-3 text-3xl font-semibold tracking-tight text-white">{value}</p>
      {description && <p className="mt-2 text-xs text-zinc-500">{description}</p>}
    </div>
  );
}
