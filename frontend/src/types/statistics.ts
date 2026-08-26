export interface MeasurementSummary {
  mean: number | null
  max: number | null
  min: number | null
  /** Non-null values contributing to the stats, not a sum of observationCount. */
  count: number
}

export interface ObservationSummary {
  temperature: MeasurementSummary
  pressure: MeasurementSummary
  windSpeed: MeasurementSummary
  windSpeedMax: MeasurementSummary
  /** Sum of observationCount across rows: raw AEMET readings underlying the (possibly aggregated) rows. */
  totalObservationCount: number
  periodStart: string | null
  periodEnd: string | null
}

export interface WindSpeedBucket {
  rangeLabel: string
  rangeMin: number
  rangeMax: number
  count: number
}
