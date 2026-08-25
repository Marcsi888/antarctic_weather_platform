// Mirrors backend/app/api/routes/observations.py and
// backend/app/api/schemas.py exactly. These are string literal unions,
// not TypeScript enums, so the values used here are identical to the
// query-string values the backend actually accepts  (no translation)
// step between the two that could drift out of sync.

export type Station = 'gabriel_de_castilla' | 'juan_carlos_i'

export type Measurement = 'temperature' | 'pressure' | 'speed'

export type AggregationLevel = 'none' | 'hourly' | 'daily' | 'monthly'

export interface ObservationQuery {
  station: Station
  /** YYYY-MM-DDTHH:MM:SS, local to `timezone`. No UTC offset: the backend
   * rejects one, since timezone is a separate field. */
  start: string
  end: string
  /** IANA timezone name. Omit to default to Europe/Madrid on the backend. */
  timezone?: string
  aggregation: AggregationLevel
  /** Empty selection is meaningful: the backend returns all three
   * measurements when none are explicitly requested. */
  measurements: readonly Measurement[]
}

export interface ObservationResponse {
  /** Always Europe/Madrid with an explicit UTC offset, e.g. "+01:00". */
  datetime: string
  temperatureCelsius: number | null
  pressureHpa: number | null
  windSpeedMs: number | null
  /** Maximum, not a separately selectable measurement: turbine operation
   * has minimum/maximum/optimal wind-speed thresholds, so the mean alone
   * can conceal a gust relevant to a wind-farm feasibility assessment. */
  windSpeedMaxMs: number | null
  observationCount: number
}
