import { AlertTriangle, BookOpen, Bot, CheckCircle2, Clock3, ShieldAlert } from 'lucide-react'
import type { IncidentAssessment, Severity } from '../types/api'

const severityStyle: Record<Severity, string> = {
  SEV1: 'bg-red-100 text-red-800 border-red-200',
  SEV2: 'bg-orange-100 text-orange-800 border-orange-200',
  SEV3: 'bg-amber-100 text-amber-800 border-amber-200',
  SEV4: 'bg-emerald-100 text-emerald-800 border-emerald-200',
}

interface Props { assessment: IncidentAssessment }

export function AssessmentCard({ assessment }: Props) {
  return (
    <section aria-label="Incident assessment" className="panel overflow-hidden">
      <div className="border-b border-ink/10 bg-ink px-6 py-5 text-white">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div><p className="mb-2 text-[11px] font-bold uppercase tracking-[.18em] text-white/55">Validated assessment</p><h2 className="max-w-3xl font-display text-2xl leading-tight">{assessment.summary}</h2></div>
          <span className={`rounded-full border px-3 py-1 text-xs font-extrabold ${severityStyle[assessment.severity]}`}>{assessment.severity}</span>
        </div>
        <div className="mt-5 flex flex-wrap gap-x-5 gap-y-2 text-xs text-white/65">
          <span className="flex items-center gap-1.5"><Bot size={14} />{assessment.provider_used}</span>
          <span className="flex items-center gap-1.5"><Clock3 size={14} />{assessment.processing_time_ms} ms</span>
          <span>{Math.round(assessment.confidence * 100)}% confidence</span>
          {assessment.cache_hit && <span>cache hit</span>}
        </div>
      </div>
      {assessment.fallback_used && <div role="alert" className="flex gap-3 border-b border-amber-200 bg-amber-50 px-6 py-4 text-sm text-amber-900"><AlertTriangle className="shrink-0" size={19} /><span><strong>Fallback assessment.</strong> The primary provider was unavailable or returned invalid output. Human review is required.</span></div>}
      <div className="grid gap-8 p-6 lg:grid-cols-2">
        <div>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-bold"><ShieldAlert size={17} className="text-signal" />Likely causes</h3>
          <ul className="space-y-2 text-sm text-ink/75">{assessment.likely_causes.map((item) => <li key={item} className="rounded-xl bg-canvas px-4 py-3">{item}</li>)}</ul>
        </div>
        <div>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-bold"><CheckCircle2 size={17} className="text-moss" />Recommended actions</h3>
          <ol className="space-y-2 text-sm text-ink/75">{assessment.recommended_actions.map((item, index) => <li key={item} className="flex gap-3"><span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-moss/10 text-xs font-bold text-moss">{index + 1}</span><span className="pt-0.5">{item}</span></li>)}</ol>
        </div>
        <div>
          <h3 className="mb-3 text-sm font-bold">Evidence</h3>
          <ul className="space-y-2 font-mono text-xs text-ink/70">{assessment.evidence.map((item) => <li key={item} className="rounded-xl border border-ink/10 bg-[#f8f9f5] px-3 py-2.5">{item}</li>)}</ul>
        </div>
        <div>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-bold"><BookOpen size={17} />Referenced runbooks</h3>
          <div className="space-y-2">{assessment.runbook_references.map((runbook) => <div key={runbook.id} className="flex items-center justify-between rounded-xl border border-ink/10 px-4 py-3 text-sm"><span>{runbook.title}</span><span className="text-xs font-semibold text-moss">{Math.round(runbook.relevance * 100)}%</span></div>)}</div>
        </div>
      </div>
      {assessment.requires_human_escalation && <div className="border-t border-red-100 bg-red-50 px-6 py-3 text-sm font-semibold text-red-800">Human escalation required</div>}
    </section>
  )
}
