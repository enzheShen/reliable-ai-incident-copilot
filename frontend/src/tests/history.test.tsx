import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import { HistoryPage } from '../pages/HistoryPage'

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
