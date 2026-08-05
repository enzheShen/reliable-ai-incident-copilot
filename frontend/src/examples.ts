import type { IncidentCreate } from './types/api'

export interface IncidentExample {
  label: string
  value: IncidentCreate
}

const base = {
  environment: 'production' as const,
  started_at: '2026-08-05T10:30:00Z',
  reporter: 'synthetic-monitor',
}

export const INCIDENT_EXAMPLES: IncidentExample[] = [
  {
    label: 'API latency spike',
    value: { ...base, service_name: 'orders-api', symptoms: 'p95 latency exceeds 2.4 seconds.', logs: ['slow request route=/orders duration=2480ms'], metrics: { p95_latency_ms: 2480, error_rate: 0.08 }, recent_changes: ['release 1.4.2'] },
  },
  {
    label: 'Database saturation',
    value: { ...base, service_name: 'catalog-api', symptoms: 'Requests cannot acquire database connections.', logs: ['pool timeout: too many clients waiting'], metrics: { db_pool_used_ratio: 0.99, error_rate: 0.31 }, recent_changes: ['traffic shift'] },
  },
  {
    label: 'Redis outage',
    value: { ...base, service_name: 'session-api', symptoms: 'Cache operations fail across production.', logs: ['redis connection refused'], metrics: { cache_error_rate: 0.72, cache_hit_rate: 0.01 }, recent_changes: [] },
  },
  {
    label: 'Authentication failures',
    value: { ...base, service_name: 'identity-api', symptoms: 'Most sign-ins return 401.', logs: ['token signature validation failed against jwks'], metrics: { http_401_rate: 0.64 }, recent_changes: ['signing key rotation'] },
  },
  {
    label: 'Memory leak',
    value: { ...base, service_name: 'worker', symptoms: 'Memory grows until instances restart.', logs: ['process killed: out of memory rss=1950mb'], metrics: { rss_mb: 1950, restart_count: 7 }, recent_changes: ['release 3.1.0'] },
  },
  {
    label: 'Deployment regression',
    value: { ...base, service_name: 'checkout-api', symptoms: 'Error rate rose immediately after deployment.', logs: ['new version 2.8.0 exception rate regression'], metrics: { error_rate: 0.24, healthy_instances_ratio: 0.55 }, recent_changes: ['deployed 2.8.0'] },
  },
]
