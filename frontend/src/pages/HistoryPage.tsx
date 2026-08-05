import { ChevronLeft, ChevronRight, LoaderCircle, Search, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { getIncident, listIncidents } from '../api/client'
import { AssessmentCard } from '../components/AssessmentCard'
import type { IncidentDetail, IncidentHistoryItem, IncidentStatus, Severity } from '../types/api'

export function HistoryPage() {
  const [page, setPage] = useState(1)
  const [service, setService] = useState('')
  const [severity, setSeverity] = useState<Severity | ''>('')
  const [status, setStatus] = useState<IncidentStatus | ''>('')
  const [items, setItems] = useState<IncidentHistoryItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [detail, setDetail] = useState<IncidentDetail | null>(null)

  useEffect(() => {
    let active = true
    setLoading(true); setError('')
    void listIncidents({ page, pageSize: 10, service: service || undefined, severity, status }).then((result) => { if (active) { setItems(result.items); setTotal(result.total) } }).catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : 'Could not load incident history.') }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [page, service, severity, status])

  async function open(id: string) { try { setDetail(await getIncident(id)) } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not load incident.') } }
  const pages = Math.max(1, Math.ceil(total / 10))

  return <div className="space-y-6"><div><p className="eyebrow mb-3">Audit trail</p><h1 className="font-display text-4xl">Incident history</h1><p className="mt-3 text-sm text-ink/55">Review persisted inputs, assessments, provider paths, and linked operational guidance.</p></div><section className="panel p-5"><div className="grid gap-3 md:grid-cols-[1fr_180px_180px]"><label className="relative"><span className="sr-only">Filter by service</span><Search className="absolute left-3 top-3 text-ink/35" size={17} /><input aria-label="Filter by service" className="field pl-10" placeholder="Service name" value={service} onChange={(event) => { setPage(1); setService(event.target.value) }} /></label><select aria-label="Filter by severity" className="field" value={severity} onChange={(event) => { setPage(1); setSeverity(event.target.value as Severity | '') }}><option value="">All severities</option>{['SEV1', 'SEV2', 'SEV3', 'SEV4'].map((value) => <option key={value}>{value}</option>)}</select><select aria-label="Filter by status" className="field" value={status} onChange={(event) => { setPage(1); setStatus(event.target.value as IncidentStatus | '') }}><option value="">All statuses</option><option value="assessed">Assessed</option><option value="pending">Pending</option></select></div></section>{error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>}<section className="panel overflow-hidden"><div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="border-b border-ink/10 bg-[#f8f9f5] text-[11px] uppercase tracking-[.14em] text-ink/45"><tr><th className="px-5 py-3">Service</th><th className="px-5 py-3">Started</th><th className="px-5 py-3">Environment</th><th className="px-5 py-3">Severity</th><th className="px-5 py-3">Status</th><th className="px-5 py-3"></th></tr></thead><tbody className="divide-y divide-ink/8">{loading ? <tr><td colSpan={6} className="px-5 py-16 text-center"><LoaderCircle className="mx-auto animate-spin text-moss" /></td></tr> : items.length === 0 ? <tr><td colSpan={6} className="px-5 py-16 text-center text-ink/45">No incidents match these filters.</td></tr> : items.map((item) => <tr key={item.id} className="hover:bg-canvas/60"><td className="px-5 py-4 font-semibold">{item.service_name}<p className="mt-1 max-w-xs truncate text-xs font-normal text-ink/45">{item.summary ?? 'Awaiting assessment'}</p></td><td className="px-5 py-4 text-ink/60">{new Date(item.started_at).toLocaleString()}</td><td className="px-5 py-4 capitalize text-ink/60">{item.environment}</td><td className="px-5 py-4 font-bold">{item.severity ?? '—'}</td><td className="px-5 py-4"><span className="rounded-full bg-moss/10 px-2.5 py-1 text-xs font-semibold capitalize text-moss">{item.status}</span></td><td className="px-5 py-4 text-right"><button className="text-xs font-bold text-moss hover:underline" onClick={() => void open(item.id)}>Open details</button></td></tr>)}</tbody></table></div><div className="flex items-center justify-between border-t border-ink/10 px-5 py-4 text-xs text-ink/55"><span>{total} incidents · page {page} of {pages}</span><div className="flex gap-2"><button aria-label="Previous page" className="rounded-lg border border-ink/10 p-2 disabled:opacity-30" disabled={page === 1} onClick={() => setPage((value) => value - 1)}><ChevronLeft size={16} /></button><button aria-label="Next page" className="rounded-lg border border-ink/10 p-2 disabled:opacity-30" disabled={page >= pages} onClick={() => setPage((value) => value + 1)}><ChevronRight size={16} /></button></div></div></section>{detail && <div className="fixed inset-0 z-50 overflow-y-auto bg-ink/55 p-4 backdrop-blur-sm" role="dialog" aria-modal="true"><div className="mx-auto my-8 max-w-5xl space-y-4"><div className="flex justify-end"><button className="rounded-full bg-white p-2 shadow" aria-label="Close details" onClick={() => setDetail(null)}><X /></button></div>{detail.assessment ? <AssessmentCard assessment={detail.assessment} /> : <div className="panel p-8">This incident has no assessment yet.</div>}</div></div>}</div>
}
