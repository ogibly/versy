interface StatusBadgeProps {
  label: string | null | undefined
}

const COLORS: Record<string, string> = {
  N: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  'N-1': 'bg-blue-100 text-blue-800 border-blue-200',
  'N-2': 'bg-amber-100 text-amber-800 border-amber-200',
  Unsupported: 'bg-rose-100 text-rose-800 border-rose-200',
}

export function StatusBadge({ label }: StatusBadgeProps) {
  const safeLabel = label ?? 'Unknown'
  const className = COLORS[safeLabel] || 'bg-slate-100 text-slate-700 border-slate-200'
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${className}`}>{safeLabel}</span>
}
