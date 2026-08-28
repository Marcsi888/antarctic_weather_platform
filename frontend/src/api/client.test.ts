import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, getLatestAvailableDate, getObservations } from './client'
import type { ObservationQuery } from '../types/api'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}
  
const baseQuery: ObservationQuery = {
  station: 'gabriel_de_castilla',
  start: '2024-01-15T00:00:00',
  end: '2024-01-15T01:00:00',
  aggregation: 'none',
  measurements: [],
}

describe('getObservations', () => {
  let fetchMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('builds the query string from all provided fields', async () => {
    fetchMock.mockResolvedValue(jsonResponse([]))

    await getObservations({
      ...baseQuery,
      timezone: 'Europe/Berlin',
      aggregation: 'daily',
      measurements: ['temperature', 'speed'],
    })

    const calledUrl = fetchMock.mock.calls[0]?.[0] as string
    const url = new URL(calledUrl)
    expect(url.pathname).toBe('/observations')
    expect(url.searchParams.get('station')).toBe('gabriel_de_castilla')
    expect(url.searchParams.get('start')).toBe('2024-01-15T00:00:00')
    expect(url.searchParams.get('timezone')).toBe('Europe/Berlin')
    expect(url.searchParams.get('aggregation')).toBe('daily')
    expect(url.searchParams.getAll('measurement')).toEqual(['temperature', 'speed'])
  })

  it('omits the timezone param entirely when not provided', async () => {
    fetchMock.mockResolvedValue(jsonResponse([]))

    await getObservations(baseQuery)

    const calledUrl = fetchMock.mock.calls[0]?.[0] as string
    expect(new URL(calledUrl).searchParams.has('timezone')).toBe(false)
  })

  it('maps snake_case response fields to camelCase', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse([
        {
          datetime: '2024-01-15T01:00:00+01:00',
          temperature_celsius: 1.4,
          pressure_hpa: 984.4,
          wind_speed_ms: 7.1,
          wind_speed_max_ms: 12.3,
          observation_count: 1,
        },
      ]),
    )

    const result = await getObservations(baseQuery)

    expect(result).toEqual([
      {
        datetime: '2024-01-15T01:00:00+01:00',
        temperatureCelsius: 1.4,
        pressureHpa: 984.4,
        windSpeedMs: 7.1,
        windSpeedMaxMs: 12.3,
        observationCount: 1,
      },
    ])
  })

  it('preserves null measurement values from the response', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse([
        {
          datetime: '2024-01-15T01:00:00+01:00',
          temperature_celsius: 1.4,
          pressure_hpa: null,
          wind_speed_ms: null,
          wind_speed_max_ms: null,
          observation_count: 1,
        },
      ]),
    )

    const [result] = await getObservations(baseQuery)

    expect(result?.pressureHpa).toBeNull()
    expect(result?.windSpeedMs).toBeNull()
    expect(result?.windSpeedMaxMs).toBeNull()
  })

  it('throws ApiError with the server detail message on a 400 response', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ detail: "Unknown station identifier: 'bogus'" }, 400),
    )

    await expect(getObservations(baseQuery)).rejects.toMatchObject({
      status: 400,
      message: "Unknown station identifier: 'bogus'",
    })
  })

  it('falls back to a generic message when an error response is not JSON', async () => {
    fetchMock.mockResolvedValue(new Response('Bad Gateway', { status: 502 }))

    await expect(getObservations(baseQuery)).rejects.toMatchObject({
      status: 502,
      message: 'Request failed with status 502',
    })
  })

  it('throws ApiError with status 0 on a network failure', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    const error = await getObservations(baseQuery).catch((e: unknown) => e)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(0)
  })

  it('throws ApiError when the response body is not a JSON array', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ unexpected: 'shape' }))

    await expect(getObservations(baseQuery)).rejects.toBeInstanceOf(ApiError)
  })

  it('throws ApiError when an array element is not an object', async () => {
    fetchMock.mockResolvedValue(jsonResponse(['not-an-object']))

    await expect(getObservations(baseQuery)).rejects.toThrow(
      'Malformed observation: expected an object',
    )
  })

  it('throws ApiError when an observation is missing datetime', async () => {
    fetchMock.mockResolvedValue(jsonResponse([{ observation_count: 1 }]))

    await expect(getObservations(baseQuery)).rejects.toThrow(
      'Malformed observation: missing datetime',
    )
  })

  it('throws ApiError when an observation is missing observation_count', async () => {
    fetchMock.mockResolvedValue(jsonResponse([{ datetime: '2024-01-15T01:00:00+01:00' }]))

    await expect(getObservations(baseQuery)).rejects.toThrow(
      'Malformed observation: missing observation_count',
    )
  })
})

describe('getLatestAvailableDate', () => {
  let fetchMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('requests the correct endpoint with the station as a query param', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ latest_available_date: '2026-03-15' }))

    await getLatestAvailableDate('gabriel_de_castilla')

    const calledUrl = fetchMock.mock.calls[0]?.[0] as string
    const url = new URL(calledUrl)
    expect(url.pathname).toBe('/observations/latest-available')
    expect(url.searchParams.get('station')).toBe('gabriel_de_castilla')
  })

  it('returns the date string on success', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ latest_available_date: '2026-03-15' }))

    const result = await getLatestAvailableDate('gabriel_de_castilla')

    expect(result).toBe('2026-03-15')
  })

  it('returns null when the backend reports no known date', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ latest_available_date: null }))

    const result = await getLatestAvailableDate('gabriel_de_castilla')

    expect(result).toBeNull()
  })

  it('returns null (fails open) on a non-2xx response, without throwing', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'boom' }, 500))

    const result = await getLatestAvailableDate('gabriel_de_castilla')

    expect(result).toBeNull()
  })

  it('returns null (fails open) on a network failure, without throwing', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    const result = await getLatestAvailableDate('gabriel_de_castilla')

    expect(result).toBeNull()
  })

  it('returns null (fails open) on a malformed response body', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ unexpected: 'shape' }))

    const result = await getLatestAvailableDate('gabriel_de_castilla')

    expect(result).toBeNull()
  })
})
