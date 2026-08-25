import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { ApiError } from './api/client'
import type { ObservationResponse } from './types/api'

vi.mock('./api/client', async () => {
  const actual = await vi.importActual<typeof import('./api/client')>('./api/client')
  return {
    ...actual,
    getObservations: vi.fn(),
  }
})

const { getObservations } = await import('./api/client')
const getObservationsMock = vi.mocked(getObservations)

const sampleObservation: ObservationResponse = {
  datetime: '2024-01-15T01:00:00+01:00',
  temperatureCelsius: 1.4,
  pressureHpa: 984.4,
  windSpeedMs: 7.1,
  windSpeedMaxMs: 9.2,
  observationCount: 1,
}

async function fillValidDateRange() {
  const user = userEvent.setup()
  const start = screen.getByLabelText('Start')
  const end = screen.getByLabelText('End')
  await user.type(start, '2024-01-15T00:00:00')
  await user.type(end, '2024-01-15T06:00:00')
  return user
}

afterEach(() => {
  getObservationsMock.mockReset()
})

describe('App', () => {
  it('shows the idle state before any query is submitted', () => {
    render(<App />)

    expect(screen.getByText('Submit a query to see observations.')).toBeInTheDocument()
  })

  it('rejects submission when start is not before end, without calling the API', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.type(screen.getByLabelText('Start'), '2024-01-15T10:00:00')
    await user.type(screen.getByLabelText('End'), '2024-01-15T09:00:00')
    await user.click(screen.getByRole('button', { name: /query/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Start must be before end.')
    expect(getObservationsMock).not.toHaveBeenCalled()
  })

  it('shows a loading state while the request is in flight, then resolves', async () => {
    let resolveRequest: (value: ObservationResponse[]) => void = () => {
      throw new Error('resolveRequest was not assigned')
    }
    getObservationsMock.mockReturnValue(
      new Promise((resolve) => {
        resolveRequest = resolve
      }),
    )
    render(<App />)
    const user = await fillValidDateRange()

    await user.click(screen.getByRole('button', { name: /query/i }))

    expect(await screen.findByRole('status')).toHaveTextContent('Loading observations…')
    expect(screen.getByRole('button', { name: /loading/i })).toBeDisabled()

    resolveRequest([sampleObservation])

    expect(await screen.findByText('2024-01-15T01:00:00+01:00')).toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('renders the results table on a successful query', async () => {
    getObservationsMock.mockResolvedValue([sampleObservation])
    render(<App />)
    const user = await fillValidDateRange()

    await user.click(screen.getByRole('button', { name: /query/i }))

    expect(await screen.findByText('2024-01-15T01:00:00+01:00')).toBeInTheDocument()
    expect(getObservationsMock).toHaveBeenCalledOnce()
  })

  it('shows an empty-state message when the query returns no observations', async () => {
    getObservationsMock.mockResolvedValue([])
    render(<App />)
    const user = await fillValidDateRange()

    await user.click(screen.getByRole('button', { name: /query/i }))

    expect(await screen.findByText(/no observations for this query/i)).toBeInTheDocument()
  })

  it('shows the API error message on a failed request', async () => {
    getObservationsMock.mockRejectedValue(new ApiError(400, "Unknown station identifier: 'x'"))
    render(<App />)
    const user = await fillValidDateRange()

    await user.click(screen.getByRole('button', { name: /query/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "Request failed: Unknown station identifier: 'x'",
    )
  })

  it('passes the selected aggregation level through to the API call', async () => {
    getObservationsMock.mockResolvedValue([sampleObservation])
    render(<App />)
    const user = await fillValidDateRange()

    await user.selectOptions(screen.getByLabelText('Aggregation'), 'daily')
    await user.click(screen.getByRole('button', { name: /query/i }))

    await waitFor(() => {
      expect(getObservationsMock).toHaveBeenCalledWith(
        expect.objectContaining({ aggregation: 'daily' }),
      )
    })
  })

  it('passes selected measurements through to the API call', async () => {
    getObservationsMock.mockResolvedValue([sampleObservation])
    render(<App />)
    const user = await fillValidDateRange()

    await user.click(screen.getByLabelText('Temperature'))
    await user.click(screen.getByRole('button', { name: /query/i }))

    await waitFor(() => {
      expect(getObservationsMock).toHaveBeenCalledWith(
        expect.objectContaining({ measurements: ['temperature'] }),
      )
    })
  })

  it('switching station changes the submitted query', async () => {
    getObservationsMock.mockResolvedValue([sampleObservation])
    render(<App />)
    const user = await fillValidDateRange()

    await user.selectOptions(screen.getByLabelText('Station'), 'juan_carlos_i')
    await user.click(screen.getByRole('button', { name: /query/i }))

    await waitFor(() => {
      expect(getObservationsMock).toHaveBeenCalledWith(
        expect.objectContaining({ station: 'juan_carlos_i' }),
      )
    })
  })
})
