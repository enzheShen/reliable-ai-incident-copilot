import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AnalysePage } from '../pages/AnalysePage'
import type { IncidentAssessment } from '../types/api'

const assessment: IncidentAssessment = {
  incident_id: '47f0db93-aee9-4278-afc1-c24655497805',
  severity: 'SEV2',
  summary: 'Redis is unavailable to the session API.',
  likely_causes: ['Redis outage'],
  evidence: ['redis connection refused'],
  recommended_actions: ['Check reachability', 'Restore the primary'],
  runbook_references: [{ id: '00000000-0000-4000-8000-000000000003', title: 'Redis outage', relevance: 0.91 }],
  confidence: 0.9,
  requires_human_escalation: true,
  provider_used: 'deterministic-mock',
  fallback_used: false,
  processing_time_ms: 42,
  created_at: '2026-08-05T10:30:01Z',
  cache_hit: false,
}

function response(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response
}

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })

describe('AnalysePage', () => {
  it('shows JSON and field validation errors without calling the API', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    render(<AnalysePage />)
    fireEvent.change(screen.getByLabelText('Incident JSON'), { target: { value: '{bad json' } })
    await userEvent.click(screen.getByRole('button', { name: /analyse incident/i }))
    expect(screen.getByRole('alert')).toHaveTextContent('JSON syntax is invalid')
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('shows loading then renders a successful structured assessment', async () => {
    let resolveRequest: ((value: Response) => void) | undefined
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>((resolve) => { resolveRequest = resolve })))
    render(<AnalysePage />)
    await userEvent.click(screen.getByRole('button', { name: /analyse incident/i }))
    expect(screen.getByRole('status')).toHaveTextContent('Applying reliability controls')
    resolveRequest?.(response(assessment))
    expect(await screen.findByRole('region', { name: 'Incident assessment' })).toHaveTextContent('Redis is unavailable')
    expect(screen.getByText('deterministic-mock')).toBeInTheDocument()
    expect(screen.getByText('42 ms')).toBeInTheDocument()
    expect(screen.getAllByText('Redis outage').length).toBeGreaterThan(0)
  })

  it('renders the explicit fallback warning', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => response({ ...assessment, provider_used: 'rule-based-fallback', fallback_used: true })))
    render(<AnalysePage />)
    await userEvent.click(screen.getByRole('button', { name: /analyse incident/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Fallback assessment')
    expect(screen.getByText('Human escalation required')).toBeInTheDocument()
  })

  it('renders an API error state', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => response({ detail: 'Rate limit exceeded' }, 429)))
    render(<AnalysePage />)
    await userEvent.click(screen.getByRole('button', { name: /analyse incident/i }))
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Rate limit exceeded'))
  })
})
