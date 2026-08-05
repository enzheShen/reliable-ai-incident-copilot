import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { ArchitecturePage } from '../pages/ArchitecturePage'

it('renders architecture, SLO targets, and GitHub documentation links', () => {
  render(<ArchitecturePage />)
  expect(screen.getByRole('heading', { name: /modular monolith/i })).toBeInTheDocument()
  expect(screen.getByText('99.5% success')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: /architecture.md/i })).toHaveAttribute(
    'href',
    expect.stringContaining('github.com/enzheShen/reliable-ai-incident-copilot'),
  )
})
