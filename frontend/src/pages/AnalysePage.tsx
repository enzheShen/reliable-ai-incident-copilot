import { Braces, LoaderCircle, Play, RotateCcw } from 'lucide-react'
import { useState } from 'react'
import { analyseIncident } from '../api/client'
import { AssessmentCard } from '../components/AssessmentCard'
import { INCIDENT_EXAMPLES } from '../examples'
import type { IncidentAssessment, IncidentCreate } from '../types/api'

function pretty(value: IncidentCreate) { return JSON.stringify(value, null, 2) }

export function validateIncident(value: unknown): string[] {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return ['Incident must be a JSON object.']
  const item = value as Record<string, unknown>
  const errors: string[] = []
  if (typeof item.service_name !== 'string' || !item.service_name.trim()) errors.push('service_name is required.')
  if (!['development', 'staging', 'production'].includes(String(item.environment))) errors.push('environment must be development, staging, or production.')
  if (typeof item.started_at !== 'string' || Number.isNaN(Date.parse(item.started_at))) errors.push('started_at must be an ISO datetime.')
  if (typeof item.symptoms !== 'string' || item.symptoms.length < 5) errors.push('symptoms must contain at least 5 characters.')
  if (!Array.isArray(item.logs) || !item.logs.every((entry) => typeof entry === 'string')) errors.push('logs must be a string array.')
  if (!item.metrics || typeof item.metrics !== 'object' || Array.isArray(item.metrics) || !Object.values(item.metrics).every((entry) => typeof entry === 'number')) errors.push('metrics must map names to numbers.')
  if (!Array.isArray(item.recent_changes) || !item.recent_changes.every((entry) => typeof entry === 'string')) errors.push('recent_changes must be a string array.')
  return errors
}

export function AnalysePage() {
  const [selected, setSelected] = useState(0)
  const [json, setJson] = useState(pretty(INCIDENT_EXAMPLES[0].value))
  const [errors, setErrors] = useState<string[]>([])
  const [assessment, setAssessment] = useState<IncidentAssessment | null>(null)
  const [loading, setLoading] = useState(false)
  const [apiError, setApiError] = useState('')

  function choose(index: number) { setSelected(index); setJson(pretty(INCIDENT_EXAMPLES[index].value)); setErrors([]); setAssessment(null); setApiError('') }
  async function submit() {
    setApiError(''); setAssessment(null)
    let parsed: unknown
    try { parsed = JSON.parse(json) } catch { setErrors(['JSON syntax is invalid.']); return }
    const validation = validateIncident(parsed)
    setErrors(validation)
    if (validation.length) return
    setLoading(true)
    try { setAssessment(await analyseIncident(parsed as IncidentCreate)) } catch (error) { setApiError(error instanceof Error ? error.message : 'Analysis request failed.') } finally { setLoading(false) }
  }

  return <div className="space-y-8">
    <div className="grid items-end gap-6 lg:grid-cols-[1fr_auto]"><div><p className="eyebrow mb-3">Evidence before action</p><h1 className="max-w-3xl font-display text-4xl leading-tight sm:text-5xl">Turn noisy signals into a reviewable incident assessment.</h1><p className="mt-4 max-w-2xl text-sm leading-6 text-ink/60">Submit structured synthetic telemetry. The backend retrieves versioned runbooks, validates provider output, and marks every degraded answer.</p></div><div className="hidden h-24 w-24 place-items-center rounded-full border border-ink/10 bg-white text-moss lg:grid"><Braces size={34} /></div></div>
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(340px,.95fr)]">
      <section className="panel p-5 sm:p-6"><div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><p className="eyebrow">Incident payload</p><p className="mt-1 text-xs text-ink/50">Maximum request size: 64 KiB</p></div><button className="flex items-center gap-1.5 text-xs font-semibold text-ink/55 hover:text-ink" onClick={() => choose(selected)}><RotateCcw size={14} />Reset example</button></div><label className="mb-2 block text-xs font-semibold" htmlFor="example">Built-in scenario</label><select id="example" className="field mb-4" value={selected} onChange={(event) => choose(Number(event.target.value))}>{INCIDENT_EXAMPLES.map((example, index) => <option value={index} key={example.label}>{example.label}</option>)}</select><label className="mb-2 block text-xs font-semibold" htmlFor="payload">Incident JSON</label><textarea id="payload" aria-label="Incident JSON" className="field min-h-[420px] resize-y font-mono text-xs leading-5" value={json} onChange={(event) => setJson(event.target.value)} spellCheck={false} />{errors.length > 0 && <div role="alert" className="mt-3 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-800"><p className="font-bold">Fix these fields:</p><ul className="mt-1 list-disc pl-4">{errors.map((error) => <li key={error}>{error}</li>)}</ul></div>}<button className="button-primary mt-4 w-full" disabled={loading} onClick={submit}>{loading ? <><LoaderCircle className="animate-spin" size={17} />Analysing incident…</> : <><Play size={16} fill="currentColor" />Analyse incident</>}</button></section>
      <aside className="space-y-4"><div className="panel p-6"><p className="eyebrow mb-4">Analysis contract</p><div className="space-y-4 text-sm"><div className="flex gap-3"><span className="font-display text-2xl text-signal">01</span><p><strong className="block">Retrieve</strong><span className="text-ink/55">Rank versioned runbooks against incident evidence.</span></p></div><div className="flex gap-3"><span className="font-display text-2xl text-signal">02</span><p><strong className="block">Validate</strong><span className="text-ink/55">Accept only schema-valid structured provider output.</span></p></div><div className="flex gap-3"><span className="font-display text-2xl text-signal">03</span><p><strong className="block">Degrade safely</strong><span className="text-ink/55">Fallback responses always demand human escalation.</span></p></div></div></div>{apiError && <div role="alert" className="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-800"><strong>Analysis failed.</strong><p className="mt-1">{apiError}</p></div>}{loading && <div role="status" className="panel grid min-h-48 place-items-center p-6 text-center"><div><LoaderCircle className="mx-auto animate-spin text-moss" /><p className="mt-3 text-sm font-semibold">Applying reliability controls</p><p className="mt-1 text-xs text-ink/50">Retrieval · provider · validation · persistence</p></div></div>}</aside>
    </div>
    {assessment && <AssessmentCard assessment={assessment} />}
  </div>
}
