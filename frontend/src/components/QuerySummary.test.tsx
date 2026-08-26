import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { QuerySummary } from './QuerySummary'
import type { ObservationQuery, ObservationResponse } from '../types/api'

const baseQuery: ObservationQuery = {
  station: 'gabriel_de_castilla',
  start: '2024-01-15T00:00:00',
  end: '2024-01-16T00:00:00',
  aggregation: 'none',
  measurements: [],
}

const rows: ObservationResponse[] = [
  {
    datetime: '2024-01-15T01:00:00+01:00',
    temperatureCelsius: 1.4,
    pressureHpa: 984.4,
    windSpeedMs: 7.1,
    windSpeedMaxMs: 9.2,
    observationCount: 6,
  },
  {
    datetime: '2024-01-15T02:00:00+01:00',
    temperatureCelsius: 1.6,
    pressureHpa: 985.0,
    windSpeedMs: 6.9,
    windSpeedMaxMs: 8.8,
    observationCount: 6,
  },
]

describe('QuerySummary', () => {
  it('displays the human-readable station label for gabriel_de_castilla', () => {
    render(<QuerySummary query={baseQuery} data={rows} />)
    expect(screen.getByText('Gabriel de Castilla')).toBeInTheDocument()
  })

  it('displays the human-readable station label for juan_carlos_i', () => {
    render(<QuerySummary query={{ ...baseQuery, station: 'juan_carlos_i' }} data={rows} />)
    expect(screen.getByText('Juan Carlos I')).toBeInTheDocument()
  })

  it('displays "All" when no measurements were explicitly requested', () => {
    render(<QuerySummary query={baseQuery} data={rows} />)
    expect(screen.getByText('All')).toBeInTheDocument()
  })

  it('displays the joined measurement list when specific measurements were requested', () => {
    render(
      <QuerySummary
        query={{ ...baseQuery, measurements: ['temperature', 'speed'] }}
        data={rows}
      />,
    )
    expect(screen.getByText('temperature, speed')).toBeInTheDocument()
  })

  it('displays the server-default timezone wording when timezone is undefined', () => {
    render(<QuerySummary query={baseQuery} data={rows} />)
    expect(screen.getByText('Europe/Madrid (server default)')).toBeInTheDocument()
  })

  it('displays the explicit timezone when one was provided', () => {
    render(<QuerySummary query={{ ...baseQuery, timezone: 'America/Argentina/Ushuaia' }} data={rows} />)
    expect(screen.getByText('America/Argentina/Ushuaia')).toBeInTheDocument()
  })

  it('displays the requested range and the actual returned period as distinct values', () => {
    render(<QuerySummary query={baseQuery} data={rows} />)

    expect(screen.getByText('2024-01-15T00:00:00 – 2024-01-16T00:00:00')).toBeInTheDocument()
    expect(
      screen.getByText('2024-01-15T01:00:00+01:00 – 2024-01-15T02:00:00+01:00'),
    ).toBeInTheDocument()
  })

  it('distinguishes row count from total raw observation count', () => {
    render(<QuerySummary query={baseQuery} data={rows} />)
    expect(screen.getByText('2 rows / 12 raw readings')).toBeInTheDocument()
  })

  it('shows a placeholder returned period when data is empty', () => {
    render(<QuerySummary query={baseQuery} data={[]} />)
    const returnedPeriodRow = screen.getByText('Returned period').closest('div')
    expect(returnedPeriodRow).toHaveTextContent('—')
  })
})
