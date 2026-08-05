import type { LucideIcon } from 'lucide-react'

interface Props { label: string; value: string; detail: string; icon: LucideIcon }

export function StatCard({ label, value, detail, icon: Icon }: Props) {
  return <div className="panel p-5"><div className="mb-5 flex items-center justify-between"><span className="eyebrow">{label}</span><span className="rounded-lg bg-moss/10 p-2 text-moss"><Icon size={17} /></span></div><p className="text-3xl font-bold tracking-tight">{value}</p><p className="mt-1 text-xs text-ink/50">{detail}</p></div>
}
