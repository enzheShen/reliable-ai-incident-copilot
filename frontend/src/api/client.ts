import type {
  IncidentAssessment,
  IncidentCreate,
  IncidentDetail,
  IncidentHistoryItem,
  IncidentStatus,
  PaginatedResponse,
  ReliabilityEvent,
  ReliabilitySummary,
  Severity,
} from '../types/api'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new ApiError(body?.detail ?? `Request failed with status ${response.status}`, response.status)
  }
  return response.json() as Promise<T>
}

export function analyseIncident(payload: IncidentCreate): Promise<IncidentAssessment> {
  return request('/incidents/analyse', {
    method: 'POST',
    body: JSON.stringify(payload),
    headers: { 'Idempotency-Key': crypto.randomUUID() },
  })
}

export interface HistoryFilters {
  page: number
  pageSize: number
  service?: string
  severity?: Severity | ''
  status?: IncidentStatus | ''
}

export function listIncidents(filters: HistoryFilters): Promise<PaginatedResponse<IncidentHistoryItem>> {
  const query = new URLSearchParams({ page: String(filters.page), page_size: String(filters.pageSize) })
  if (filters.service) query.set('service', filters.service)
  if (filters.severity) query.set('severity', filters.severity)
  if (filters.status) query.set('status', filters.status)
  return request(`/incidents?${query}`)
}

export function getIncident(id: string): Promise<IncidentDetail> {
  return request(`/incidents/${id}`)
}

export function getReliabilitySummary(windowMinutes = 60): Promise<ReliabilitySummary> {
  return request(`/reliability/summary?window_minutes=${windowMinutes}`)
}

export function getReliabilityEvents(windowMinutes = 60): Promise<ReliabilityEvent[]> {
  return request(`/reliability/events?window_minutes=${windowMinutes}`)
}
