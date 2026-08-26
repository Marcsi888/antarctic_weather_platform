import { describe, expect, it } from 'vitest'
import { bucketWindSpeed, summarize, summarizeMeasurement } from './statistics'
import type { ObservationResponse } from '../types/api'

function obs(overrides: Partial<ObservationResponse> = {}): ObservationResponse {
  return {
    datetime: '2024-01-15T00:00:00+01:00',
    temperatureCelsius: null,
    pressureHpa: null,
    windSpeedMs: null,
    windSpeedMaxMs: null,
    observationCount: 1,
    ...overrides,
  }
}

describe('summarizeMeasurement', () => {
  it('returns all-null/zero-count for an empty array', () => {
    expect(summarizeMeasurement([])).toEqual({ mean: null, max: null, min: null, count: 0 })
  })

  it('returns all-null/zero-count for an all-null array, not a real zero value', () => {
    expect(summarizeMeasurement([null, null])).toEqual({
      mean: null,
      max: null,
      min: null,
      count: 0,
    })
  })

  it('excludes nulls from mean/max/min while counting only non-null entries', () => {
    const result = summarizeMeasurement([1, null, 5, null, 3])
    expect(result).toEqual({ mean: 3, max: 5, min: 1, count: 3 })
  })

  it('computes correct mean/max/min for a known fixture', () => {
    expect(summarizeMeasurement([1, 3, 5])).toEqual({ mean: 3, max: 5, min: 1, count: 3 })
  })
})

describe('summarize', () => {
  it('returns null periodStart/periodEnd for an empty array', () => {
    const result = summarize([])
    expect(result.periodStart).toBeNull()
    expect(result.periodEnd).toBeNull()
    expect(result.totalObservationCount).toBe(0)
  })

  it('derives periodStart/periodEnd from the first/last row', () => {
    const data = [
      obs({ datetime: '2024-01-15T00:00:00+01:00' }),
      obs({ datetime: '2024-01-15T01:00:00+01:00' }),
      obs({ datetime: '2024-01-15T02:00:00+01:00' }),
    ]
    const result = summarize(data)
    expect(result.periodStart).toBe('2024-01-15T00:00:00+01:00')
    expect(result.periodEnd).toBe('2024-01-15T02:00:00+01:00')
  })

  it('sums observationCount across rows', () => {
    const data = [obs({ observationCount: 6 }), obs({ observationCount: 6 }), obs({ observationCount: 3 })]
    expect(summarize(data).totalObservationCount).toBe(15)
  })

  it('summarizes each measurement independently', () => {
    const data = [
      obs({ temperatureCelsius: 1, windSpeedMs: 5, windSpeedMaxMs: 9 }),
      obs({ temperatureCelsius: 3, windSpeedMs: 7, windSpeedMaxMs: 11 }),
    ]
    const result = summarize(data)
    expect(result.temperature).toEqual({ mean: 2, max: 3, min: 1, count: 2 })
    expect(result.windSpeed).toEqual({ mean: 6, max: 7, min: 5, count: 2 })
    expect(result.windSpeedMax).toEqual({ mean: 10, max: 11, min: 9, count: 2 })
    expect(result.pressure).toEqual({ mean: null, max: null, min: null, count: 0 })
  })
})

describe('bucketWindSpeed', () => {
  it('returns an empty array when all windSpeedMs values are null', () => {
    expect(bucketWindSpeed([obs(), obs()])).toEqual([])
  })

  it('returns an empty array for an empty dataset', () => {
    expect(bucketWindSpeed([])).toEqual([])
  })

  it('assigns values to correct buckets for a fixed bucket size', () => {
    const data = [
      obs({ windSpeedMs: 1 }),
      obs({ windSpeedMs: 3 }),
      obs({ windSpeedMs: 7 }),
    ]
    const buckets = bucketWindSpeed(data, 2)

    // min=1, max=7 -> buckets [1,3) [3,5) [5,7]
    expect(buckets).toHaveLength(3)
    expect(buckets[0]).toMatchObject({ count: 1 })
    expect(buckets[1]).toMatchObject({ count: 1 })
    expect(buckets[2]).toMatchObject({ count: 1 })
  })

  it('handles a single distinct value without dividing by zero', () => {
    const data = [obs({ windSpeedMs: 5 }), obs({ windSpeedMs: 5 })]
    const buckets = bucketWindSpeed(data)

    expect(buckets).toHaveLength(1)
    expect(buckets[0]).toMatchObject({ rangeMin: 5, rangeMax: 5, count: 2 })
  })

  it('does not produce NaN or Infinity bucket boundaries', () => {
    const data = [obs({ windSpeedMs: 2 }), obs({ windSpeedMs: 2 })]
    const buckets = bucketWindSpeed(data)

    for (const bucket of buckets) {
      expect(Number.isFinite(bucket.rangeMin)).toBe(true)
      expect(Number.isFinite(bucket.rangeMax)).toBe(true)
      expect(Number.isNaN(bucket.count)).toBe(false)
    }
  })

  it('places the maximum value in the last bucket, not overflowing past it', () => {
    const data = [obs({ windSpeedMs: 0 }), obs({ windSpeedMs: 10 })]
    const buckets = bucketWindSpeed(data, 5)

    const total = buckets.reduce((sum, b) => sum + b.count, 0)
    expect(total).toBe(2)
    const lastBucket = buckets[buckets.length - 1]
    expect(lastBucket?.count).toBeGreaterThan(0)
  })
})
