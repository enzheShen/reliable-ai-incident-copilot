export type Environment = 'development' | 'staging' | 'production'
export type Severity = 'SEV1' | 'SEV2' | 'SEV3' | 'SEV4'
export type IncidentStatus = 'pending' | 'assessed'

export interface IncidentCreate {
  service_name: string
  environment: Environment
  started_at: string
  symptoms: string
  logs: string[]
  metrics: Record<string, number>
  recent_changes: string[]
  reporter?: string | null
}

export interface RunbookReference {
  id: string
  title: string
  relevance: number
}

export interface IncidentAssessment {
  incident_id: string
  severity: Severity
  summary: string
  likely_causes: string[]
  evidence: string[]
  recommended_actions: string[]
  runbook_references: RunbookReference[]
  confidence: number
  requires_human_escalation: boolean
  provider_used: string
  fallback_used: boolean
  processing_time_ms: number
  created_at: string
  cache_hit: boolean
}

export interface IncidentHistoryItem {
  id: string
  service_name: string
  environment: Environment
  started_at: string
  created_at: string
  status: IncidentStatus
  severity: Severity | null
  summary: string | null
}

export interface IncidentDetail {
  id: string
  incident: IncidentCreate
  assessment: IncidentAssessment | null
  created_at: string
}

export interface PaginatedResponse<T> {
  page: number
  page_size: number
  total: number
  items: T[]
}

export interface LatencyPoint {
  time: string
  p50: number
  p95: number
}

export interface ReliabilitySummary {
  window_minutes: number
  request_count: number
  success_rate: number
  p50_latency_ms: number
  p95_latency_ms: number
  fallback_count: number
  cache_hit_rate: number
  provider_failure_count: number
  severity_distribution: Record<Severity, number>
  latency_series: LatencyPoint[]
}

export interface ReliabilityEvent {
  id: string
  event_type: string
  provider: string | null
  details: Record<string, unknown>
  created_at: string
}
