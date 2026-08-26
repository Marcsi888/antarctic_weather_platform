import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { WindDistributionChart } from './WindDistributionChart'
import type { ObservationResponse } from '../types/api'

function obs(windSpeedMs: number | null): ObservationResponse {
  return {
    datetime: '2024-01-15T00:00:00+01:00',
    temperatureCelsius: null,
    pressureHpa: null,
    windSpeedMs,
    windSpeedMaxMs: null,
    observationCount: 1,
  }
}

describe('WindDistributionChart', () => {
  it('renders an empty-state message when all wind speed values are null', () => {
    render(<WindDistributionChart data={[obs(null), obs(null)]} />)

    expect(screen.getByText(/no wind speed data available/i)).toBeInTheDocument()
  })

  it('renders an empty-state message for an empty dataset', () => {
    render(<WindDistributionChart data={[]} />)

    expect(screen.getByText(/no wind speed data available/i)).toBeInTheDocument()
  })

  it('renders a chart region for a varied fixture', () => {
    const { container } = render(
      <WindDistributionChart data={[obs(1), obs(3), obs(5), obs(7)]} />,
    )

    expect(screen.queryByText(/no wind speed data available/i)).not.toBeInTheDocument()
    expect(container.querySelector('.recharts-responsive-container')).not.toBeNull()
  })

  it('renders without throwing for a single-value (degenerate) dataset', () => {
    const { container } = render(<WindDistributionChart data={[obs(5), obs(5)]} />)

    expect(container.querySelector('.recharts-responsive-container')).not.toBeNull()
  })
})
