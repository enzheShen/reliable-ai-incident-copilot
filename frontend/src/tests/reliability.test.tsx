import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ReliabilityPage } from '../pages/ReliabilityPage'
import type { ReliabilitySummary } from '../types/api'

const summary: ReliabilitySummary = {
  window_minutes: 60,
  request_count: 4,
  success_rate: 0.75,
  p50_latency_ms: 20,
  p95_latency_ms: 80,
  fallback_count: 1,
  cache_hit_rate: 0.5,
  provider_failure_count: 1,
  severity_distribution: { SEV1: 0, SEV2: 3, SEV3: 0, SEV4: 0 },
  latency_series: [{ time: '2026-08-05T10:00:00+00:00', p50: 20, p95: 80 }],
}

function response(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('ReliabilityPage', () => {
  it('renders measured success, fallback, cache, and provider values for one window', async () => {
    const fetchMock = vi.fn(async (url: string) =>
      response(url.includes('/summary') ? summary : []),
    )
    vi.stubGlobal('fetch', fetchMock)
    render(<ReliabilityPage />)
    expect(screen.getByRole('status')).toHaveTextContent('Loading real service indicators')
    expect(await screen.findByText('75.00%')).toBeInTheDocument()
    expect(screen.getByText('50.0%')).toBeInTheDocument()
    expect(screen.getAllByText('1').length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText('No reliability events in this window.')).toBeInTheDocument()
    const urls = fetchMock.mock.calls.map(([url]) => String(url))
    expect(urls).toEqual(
      expect.arrayContaining([
        expect.stringContaining('/summary?window_minutes=60'),
        expect.stringContaining('/events?window_minutes=60'),
      ]),
    )
  })

  it('renders an explicit empty-window state', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) =>
        response(url.includes('/summary') ? { ...summary, request_count: 0, success_rate: 1 } : []),
      ),
    )
    render(<ReliabilityPage />)
    expect(await screen.findByText('No analysis requests in this window.')).toBeInTheDocument()
  })

  it('renders an API error state', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => response({ detail: 'Metrics unavailable' }, 503)))
    render(<ReliabilityPage />)
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Metrics unavailable'))
  })
})
