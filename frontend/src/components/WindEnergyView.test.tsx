import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { WindEnergyView } from './WindEnergyView'
import type { ObservationResponse } from '../types/api'

function obs(windSpeedMs: number | null, windSpeedMaxMs: number | null): ObservationResponse {
  return {
    datetime: '2024-01-15T00:00:00+01:00',
    temperatureCelsius: null,
    pressureHpa: null,
    windSpeedMs,
    windSpeedMaxMs,
    observationCount: 1,
  }
}

const windData: ObservationResponse[] = [obs(4, 6), obs(8, 12), obs(6, 9)]

describe('WindEnergyView', () => {
  it('renders the mean/max summary header with correct values', () => {
    render(<WindEnergyView data={windData} />)

    expect(screen.getByText('Mean wind speed')).toBeInTheDocument()
    expect(screen.getByText('6.0 m/s')).toBeInTheDocument() // mean of 4, 8, 6
    expect(screen.getByText('Max wind speed')).toBeInTheDocument()
    expect(screen.getByText('12.0 m/s')).toBeInTheDocument() // max of 6, 12, 9
  })

  it('renders the wind time-series and distribution regions', () => {
    const { container } = render(<WindEnergyView data={windData} />)

    const containers = container.querySelectorAll('.recharts-responsive-container')
    expect(containers.length).toBeGreaterThanOrEqual(2)
  })

  it('renders a sparse-data empty state when there is no wind speed data at all', () => {
    const noWind: ObservationResponse[] = [obs(null, null)]
    render(<WindEnergyView data={noWind} />)

    expect(screen.getByText(/no wind speed data available for this query/i)).toBeInTheDocument()
  })

  it('renders an empty state for an empty dataset', () => {
    render(<WindEnergyView data={[]} />)

    expect(screen.getByText(/no wind speed data available for this query/i)).toBeInTheDocument()
  })

  it('never renders invented turbine threshold values', () => {
    render(<WindEnergyView data={windData} />)

    expect(screen.queryByText(/cut-in|rated speed|cut-out/i)).not.toBeInTheDocument()
  })
})
