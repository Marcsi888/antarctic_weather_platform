import { useMemo } from 'react'
import type { ObservationResponse } from '../types/api'
import { summarize } from '../utils/statistics'
import { WindDistributionChart } from './WindDistributionChart'
import { WindTimeSeriesLine } from './WindTimeSeriesLine'

interface WindEnergyViewProps {
  data: readonly ObservationResponse[]
}

function formatSpeed(value: number | null): string {
  return value === null ? '—' : `${value.toFixed(1)} m/s`
}

// The distinctive wind-analysis feature: time series (typical + peak) +
// mean/max summary + distribution/variability. Deliberately does not
// print any specific turbine threshold (cut-in/rated/cut-out speed) —
// those are turbine-model-specific and not part of this API or the
// original spec. Only real mean/max numbers derived from the response,
// plus general explanatory text about why both matter, are shown.
export function WindEnergyView({ data }: WindEnergyViewProps) {
  const summary = useMemo(() => summarize(data), [data])
  const hasWindData = summary.windSpeed.count > 0 || summary.windSpeedMax.count > 0

  if (data.length === 0 || !hasWindData) {
    return (
      <p className="results-empty">
        No wind speed data available for this query. Include wind speed in the requested
        measurements, or try a different date range, to see the wind-energy analysis.
      </p>
    )
  }

  return (
    <div className="wind-energy-view">
      <div className="wind-energy-header">
        <div className="metric-card">
          <dt>Mean wind speed</dt>
          <dd>{formatSpeed(summary.windSpeed.mean)}</dd>
        </div>
        <div className="metric-card">
          <dt>Max wind speed</dt>
          <dd>{formatSpeed(summary.windSpeedMax.max)}</dd>
        </div>
      </div>

      <WindTimeSeriesLine data={data} />

      <WindDistributionChart data={data} />

      <p className="wind-energy-annotation">
        Across {summary.windSpeed.count} readings with valid wind speed, values ranged from{' '}
        {formatSpeed(summary.windSpeed.min)} to {formatSpeed(summary.windSpeedMax.max)} (mean{' '}
        {formatSpeed(summary.windSpeed.mean)}). Turbine siting decisions typically weigh both
        sustained (mean) and peak (max) conditions, since operating ranges depend on minimum,
        maximum, and optimal wind-speed thresholds specific to the turbine model under
        consideration.
      </p>
    </div>
  )
}
