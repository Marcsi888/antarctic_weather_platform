import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { SummaryMetrics } from './SummaryMetrics'
import type { ObservationResponse } from '../types/api'

const fullObservation: ObservationResponse = {
  datetime: '2024-01-15T01:00:00+01:00',
  temperatureCelsius: 1.4,
  pressureHpa: 984.4,
  windSpeedMs: 7.1,
  windSpeedMaxMs: 9.2,
  observationCount: 6,
}

describe('SummaryMetrics', () => {
  it('renders nothing for an empty dataset', () => {
    const { container } = render(<SummaryMetrics data={[]} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders all six metric labels for a full fixture', () => {
    render(<SummaryMetrics data={[fullObservation]} />)

    expect(screen.getByText('Mean wind speed')).toBeInTheDocument()
    expect(screen.getByText('Max wind speed')).toBeInTheDocument()
    expect(screen.getByText('Mean temperature')).toBeInTheDocument()
    expect(screen.getByText('Mean pressure')).toBeInTheDocument()
    expect(screen.getByText('Observations')).toBeInTheDocument()
    expect(screen.getByText('Queried period')).toBeInTheDocument()
  })

  it('computes mean as the single value for a single-row dataset', () => {
    render(<SummaryMetrics data={[fullObservation]} />)

    expect(screen.getByText('7.1 m/s')).toBeInTheDocument() // mean wind speed
    expect(screen.getByText('9.2 m/s')).toBeInTheDocument() // max wind speed
    expect(screen.getByText('1.4 °C')).toBeInTheDocument()
    expect(screen.getByText('984.4 hPa')).toBeInTheDocument()
  })

  it('renders a placeholder for a measurement that is entirely null', () => {
    const noPressure: ObservationResponse = { ...fullObservation, pressureHpa: null }
    render(<SummaryMetrics data={[noPressure]} />)

    const pressureRow = screen.getByText('Mean pressure').closest('div')
    expect(pressureRow).toHaveTextContent('—')
  })

  it('displays the row count and total raw observation count distinctly', () => {
    const rows: ObservationResponse[] = [
      fullObservation,
      { ...fullObservation, datetime: '2024-01-15T02:00:00+01:00', observationCount: 6 },
    ]
    render(<SummaryMetrics data={rows} />)

    expect(screen.getByText('2 rows / 12 readings')).toBeInTheDocument()
  })

  it('displays the queried period using the first and last datetime', () => {
    const rows: ObservationResponse[] = [
      fullObservation,
      { ...fullObservation, datetime: '2024-01-15T03:00:00+01:00' },
    ]
    render(<SummaryMetrics data={rows} />)

    expect(
      screen.getByText('2024-01-15T01:00:00+01:00 – 2024-01-15T03:00:00+01:00'),
    ).toBeInTheDocument()
  })
})
