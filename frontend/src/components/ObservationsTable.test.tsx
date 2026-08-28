import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ObservationsTable } from './ObservationsTable'
import type { ObservationResponse } from '../types/api'

const fullObservation: ObservationResponse = {
  datetime: '2024-01-15T01:00:00+01:00',
  temperatureCelsius: 1.4,
  pressureHpa: 984.4,
  windSpeedMs: 7.1,
  windSpeedMaxMs: 9.2,
  observationCount: 1,
}

describe('ObservationsTable', () => {
  it('shows an empty-state message when there are no observations', () => {
    render(<ObservationsTable data={[]} />)

    expect(screen.getByText(/no observations for this query/i)).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('renders one row per observation with formatted values', () => {
    render(<ObservationsTable data={[fullObservation]} />)

    const row = screen.getByText('2024-01-15T01:00:00+01:00').closest('tr')
    expect(row).not.toBeNull()
    expect(row).toHaveTextContent('1.4 °C')
    expect(row).toHaveTextContent('984.4 hPa')
    expect(row).toHaveTextContent('7.1 m/s')
    expect(row).toHaveTextContent('9.2 m/s')
  })

  it('renders a placeholder for null measurement values, not 0 or blank', () => {
    const partial: ObservationResponse = {
      ...fullObservation,
      pressureHpa: null,
      windSpeedMs: null,
      windSpeedMaxMs: null,
    }
    render(<ObservationsTable data={[partial]} />)

    const row = screen.getByText('2024-01-15T01:00:00+01:00').closest('tr')
    // Three null fields -> three placeholder cells, distinguishing "not
    // requested / no valid data" from a real zero value. Checked via the
    // cells themselves, not a regex over the whole row's text, since the
    // datetime cell also contains hyphens.
    const cells = row ? Array.from(row.querySelectorAll('td')) : []
    const placeholderCells = cells.filter((cell) => cell.textContent === '-')
    expect(placeholderCells).toHaveLength(3)
  })

  it('renders multiple rows in the order given', () => {
    const second: ObservationResponse = { ...fullObservation, datetime: '2024-01-15T02:00:00+01:00' }
    render(<ObservationsTable data={[fullObservation, second]} />)

    const rows = screen.getAllByRole('row')
    // First row is the header; data rows follow in the given order.
    expect(rows).toHaveLength(3)
    expect(rows[1]).toHaveTextContent('2024-01-15T01:00:00+01:00')
    expect(rows[2]).toHaveTextContent('2024-01-15T02:00:00+01:00')
  })
})
