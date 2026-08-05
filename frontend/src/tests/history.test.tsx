import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import { HistoryPage } from '../pages/HistoryPage'
import type { IncidentAssessment, IncidentHistoryItem } from '../types/api'

function response(body: unknown): Response {
  return { ok: true, status: 200, json: async () => body } as Response
}

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })

it('sends service, severity, and status history filters to the API', async () => {
  const fetchMock = vi.fn(async () => response({ page: 1, page_size: 10, total: 0, items: [] }))
  vi.stubGlobal('fetch', fetchMock)
  render(<HistoryPage />)
  await waitFor(() => expect(fetchMock).toHaveBeenCalled())
  await userEvent.type(screen.getByLabelText('Filter by service'), 'orders-api')
  await userEvent.selectOptions(screen.getByLabelText('Filter by severity'), 'SEV2')
  await userEvent.selectOptions(screen.getByLabelText('Filter by status'), 'assessed')
  await waitFor(() => {
    const calls = fetchMock.mock.calls as unknown as Array<[string]>
    const latestUrl = String(calls.at(-1)?.[0])
    expect(latestUrl).toContain('service=orders-api')
    expect(latestUrl).toContain('severity=SEV2')
    expect(latestUrl).toContain('status=assessed')
  })
})

const historyItem: IncidentHistoryItem = {
  id: '47f0db93-aee9-4278-afc1-c24655497805',
  service_name: 'orders-api',
  environment: 'production',
  started_at: '2026-08-05T10:30:00Z',
  created_at: '2026-08-05T10:31:00Z',
  status: 'assessed',
  severity: 'SEV2',
  summary: 'Orders latency is elevated.',
}

const assessment: IncidentAssessment = {
  incident_id: historyItem.id,
  severity: 'SEV2',
  summary: 'Orders latency is elevated.',
  likely_causes: ['Deployment regression'],
  evidence: ['slow request duration=2400ms'],
  recommended_actions: ['Roll back the release'],
  runbook_references: [{ id: '00000000-0000-4000-8000-000000000012', title: 'Deployment regression', relevance: 0.9 }],
  confidence: 0.9,
  requires_human_escalation: true,
  provider_used: 'deterministic-mock',
  fallback_used: false,
  processing_time_ms: 20,
  created_at: '2026-08-05T10:31:00Z',
  cache_hit: true,
}

it('moves to the next history page', async () => {
  const fetchMock = vi.fn(async () =>
    response({ page: 1, page_size: 10, total: 11, items: [historyItem] }),
  )
  vi.stubGlobal('fetch', fetchMock)
  render(<HistoryPage />)
  await screen.findByText('orders-api')
  await userEvent.click(screen.getByRole('button', { name: 'Next page' }))
  await waitFor(() => {
    const calls = fetchMock.mock.calls as unknown as Array<[string]>
    expect(String(calls.at(-1)?.[0])).toContain('page=2')
  })
})

it('opens an incident detail modal and exposes provider and cache state', async () => {
  const fetchMock = vi.fn(async (url: string) => {
    if (url.includes(`/incidents/${historyItem.id}`)) {
      return response({
        id: historyItem.id,
        incident: {
          service_name: 'orders-api',
          environment: 'production',
          started_at: historyItem.started_at,
          symptoms: 'Orders requests are slow.',
          logs: ['slow request duration=2400ms'],
          metrics: { p95_latency_ms: 2400 },
          recent_changes: ['release 1.2.0'],
        },
        assessment,
        created_at: historyItem.created_at,
      })
    }
    return response({ page: 1, page_size: 10, total: 1, items: [historyItem] })
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<HistoryPage />)
  await userEvent.click(await screen.findByRole('button', { name: 'Open details' }))
  const dialog = await screen.findByRole('dialog')
  expect(dialog).toHaveTextContent('deterministic-mock')
  expect(dialog).toHaveTextContent('cache hit')
  expect(dialog).toHaveTextContent('Human escalation required')
})
