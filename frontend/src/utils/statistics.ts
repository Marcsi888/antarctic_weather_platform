import type { ObservationResponse } from '../types/api'
import type { MeasurementSummary, ObservationSummary, WindSpeedBucket } from '../types/statistics'

export function summarizeMeasurement(values: readonly (number | null)[]): MeasurementSummary {
  const present = values.filter((v): v is number => v !== null)
  if (present.length === 0) {
    return { mean: null, max: null, min: null, count: 0 }
  }

  let sum = 0
  let max = present[0] as number
  let min = present[0] as number
  for (const value of present) {
    sum += value
    if (value > max) max = value
    if (value < min) min = value
  }

  return { mean: sum / present.length, max, min, count: present.length }
}

export function summarize(data: readonly ObservationResponse[]): ObservationSummary {
  const first = data[0]
  const last = data[data.length - 1]

  let totalObservationCount = 0
  for (const row of data) {
    totalObservationCount += row.observationCount
  }

  return {
    temperature: summarizeMeasurement(data.map((d) => d.temperatureCelsius)),
    pressure: summarizeMeasurement(data.map((d) => d.pressureHpa)),
    windSpeed: summarizeMeasurement(data.map((d) => d.windSpeedMs)),
    windSpeedMax: summarizeMeasurement(data.map((d) => d.windSpeedMaxMs)),
    totalObservationCount,
    periodStart: first === undefined ? null : first.datetime,
    periodEnd: last === undefined ? null : last.datetime,
  }
}

const DEFAULT_BUCKET_COUNT = 8

// Bucket width is derived from the data's own range rather than
// hardcoded, so a 2-hour hourly query and a multi-year monthly-aggregated
// query both degrade to a sensible number of bins instead of one giant
// bucket or dozens of empty ones.
export function bucketWindSpeed(
  data: readonly ObservationResponse[],
  bucketSizeMs?: number,
): WindSpeedBucket[] {
  const values = data
    .map((d) => d.windSpeedMs)
    .filter((v): v is number => v !== null)

  if (values.length === 0) {
    return []
  }

  const min = Math.min(...values)
  const max = Math.max(...values)

  // A single distinct value (or all values equal) has no real range to
  // bucket: report one bucket spanning that value rather than dividing
  // by a zero-width range.
  if (max === min) {
    return [
      {
        rangeLabel: `${min.toFixed(1)} m/s`,
        rangeMin: min,
        rangeMax: max,
        count: values.length,
      },
    ]
  }

  const width = bucketSizeMs ?? (max - min) / DEFAULT_BUCKET_COUNT
  const bucketCount = Math.ceil((max - min) / width)
  const buckets: WindSpeedBucket[] = Array.from({ length: bucketCount }, (_, i) => {
    const rangeMin = min + i * width
    const rangeMax = i === bucketCount - 1 ? max : rangeMin + width
    return {
      rangeLabel: `${rangeMin.toFixed(1)}–${rangeMax.toFixed(1)}`,
      rangeMin,
      rangeMax,
      count: 0,
    }
  })

  for (const value of values) {
    // The max value falls exactly on the last bucket's upper edge; every
    // other bucket boundary is treated as [min, max) to avoid double-counting.
    const index =
      value === max ? bucketCount - 1 : Math.min(Math.floor((value - min) / width), bucketCount - 1)
    const bucket = buckets[index]
    if (bucket !== undefined) {
      bucket.count += 1
    }
  }

  return buckets
}
