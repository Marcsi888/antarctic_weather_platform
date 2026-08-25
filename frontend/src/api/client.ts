import type { ObservationQuery, ObservationResponse } from '../types/api'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function buildQueryString(query: ObservationQuery): string {
  const params = new URLSearchParams({
    station: query.station,
    start: query.start,
    end: query.end,
    aggregation: query.aggregation,
  })
  if (query.timezone) {
    params.set('timezone', query.timezone)
  }
  for (const measurement of query.measurements) {
    params.append('measurement', measurement)
  }
  return params.toString()
}

// The backend's JSON keys are snake_case (matching the Python API schema);
// this is the one place that translation to the TypeScript camelCase
// convention happens, and where the untyped fetch().json() result is
// checked, not just cast, before it's trusted as ObservationResponse[].
function parseObservation(raw: unknown): ObservationResponse {
  if (typeof raw !== 'object' || raw === null) {
    throw new ApiError(0, 'Malformed observation: expected an object')
  }
  const record = raw as Record<string, unknown>

  if (typeof record.datetime !== 'string') {
    throw new ApiError(0, 'Malformed observation: missing datetime')
  }
  if (typeof record.observation_count !== 'number') {
    throw new ApiError(0, 'Malformed observation: missing observation_count')
  }

  return {
    datetime: record.datetime,
    temperatureCelsius: asNullableNumber(record.temperature_celsius),
    pressureHpa: asNullableNumber(record.pressure_hpa),
    windSpeedMs: asNullableNumber(record.wind_speed_ms),
    windSpeedMaxMs: asNullableNumber(record.wind_speed_max_ms),
    observationCount: record.observation_count,
  }
}

function asNullableNumber(value: unknown): number | null {
  return typeof value === 'number' ? value : null
}

export async function getObservations(
  query: ObservationQuery,
): Promise<ObservationResponse[]> {
  const url = `${API_BASE_URL}/observations?${buildQueryString(query)}`

  let response: Response
  try {
    response = await fetch(url)
  } catch {
    // fetch() itself throws only on network failure (offline, DNS,
    // CORS block) — never on a non-2xx status, which is handled below.
    throw new ApiError(0, 'Could not reach the server. Check your connection.')
  }

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null)
    const detail =
      body !== null && typeof body === 'object' && 'detail' in body
        ? String(body.detail)
        : `Request failed with status ${String(response.status)}`
    throw new ApiError(response.status, detail)
  }

  const data: unknown = await response.json()
  if (!Array.isArray(data)) {
    throw new ApiError(0, 'Malformed response: expected an array')
  }
  return data.map(parseObservation)
}
