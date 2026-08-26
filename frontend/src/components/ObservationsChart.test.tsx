import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ObservationsChart } from './ObservationsChart'
import type { ObservationResponse } from '../types/api'

const fullObservation: ObservationResponse = {
  datetime: '2024-01-15T01:00:00+01:00',
  temperatureCelsius: 1.4,
  pressureHpa: 984.4,
  windSpeedMs: 7.1,
  windSpeedMaxMs: 9.2,
  observationCount: 1,
}

describe('ObservationsChart', () => {
  it('renders nothing for an empty dataset', () => {
    const { container } = render(<ObservationsChart data={[]} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders nothing when every measurement is null', () => {
    const empty: ObservationResponse = {
      ...fullObservation,
      temperatureCelsius: null,
      pressureHpa: null,
      windSpeedMs: null,
      windSpeedMaxMs: null,
    }
    const { container } = render(<ObservationsChart data={[empty]} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders a panel per measurement present in the data', () => {
    render(<ObservationsChart data={[fullObservation]} />)

    expect(screen.getByRole('heading', { name: 'Temperature (°C)' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Wind speed (m/s)' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Pressure (hPa)' })).toBeInTheDocument()
  })

  it('omits the temperature panel when temperature is entirely null', () => {
    const noTemp: ObservationResponse = { ...fullObservation, temperatureCelsius: null }
    render(<ObservationsChart data={[noTemp]} />)

    expect(screen.queryByRole('heading', { name: 'Temperature (°C)' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Pressure (hPa)' })).toBeInTheDocument()
  })

  it('keeps the wind speed panel when only the max is present, not mean', () => {
    const maxOnly: ObservationResponse = { ...fullObservation, windSpeedMs: null }
    render(<ObservationsChart data={[maxOnly]} />)

    expect(screen.getByRole('heading', { name: 'Wind speed (m/s)' })).toBeInTheDocument()
  })

  it('omits the wind speed panel when both mean and max are null', () => {
    const noWind: ObservationResponse = {
      ...fullObservation,
      windSpeedMs: null,
      windSpeedMaxMs: null,
    }
    render(<ObservationsChart data={[noWind]} />)

    expect(screen.queryByRole('heading', { name: 'Wind speed (m/s)' })).not.toBeInTheDocument()
  })
})
