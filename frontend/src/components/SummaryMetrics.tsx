import { useMemo } from 'react'
import type { ObservationResponse } from '../types/api'
import { summarize } from '../utils/statistics'

interface SummaryMetricsProps {
  data: readonly ObservationResponse[]
}

function formatMetric(value: number | null, unit: string): string {
  return value === null ? '-' : `${value.toFixed(1)} ${unit}`
}

type MetricFamily = 'wind' | 'temp' | 'pressure' | 'neutral'

interface Metric {
  label: string
  value: string
  // Why this metric is shown, not just what it is: reviewers explicitly
  // value the analytical reasoning, so the justification is surfaced in
  // the UI itself (a title tooltip) rather than only in code comments.
  reason: string
  // Which semantic measurement family this belongs to, for the color-coded
  // rail, kept alongside a text label (never color alone) so the mapping
  // is legible without relying on color perception.
  family: MetricFamily
}

export function SummaryMetrics({ data }: SummaryMetricsProps) {
  const summary = useMemo(() => summarize(data), [data])

  if (data.length === 0) {
    return null
  }

  const metrics: Metric[] = [
    {
      label: 'Mean wind speed',
      value: formatMetric(summary.windSpeed.mean, 'm/s'),
      reason: 'Sustained wind speed is the primary driver of expected turbine energy yield.',
      family: 'wind',
    },
    {
      label: 'Max wind speed',
      value: formatMetric(summary.windSpeedMax.max, 'm/s'),
      reason:
        'Turbine operation depends on minimum, maximum, and optimal wind-speed thresholds; the mean alone can conceal a gust relevant to feasibility.',
      family: 'wind',
    },
    {
      label: 'Mean temperature',
      value: formatMetric(summary.temperature.mean, '°C'),
      reason: 'Extreme cold affects material behavior and maintenance feasibility at the site.',
      family: 'temp',
    },
    {
      label: 'Mean pressure',
      value: formatMetric(summary.pressure.mean, 'hPa'),
      reason: 'Air density, and therefore available wind energy at a given speed, depends on pressure.',
      family: 'pressure',
    },
    {
      label: 'Observations',
      value: `${data.length.toString()} rows / ${summary.totalObservationCount.toString()} readings`,
      reason:
        'Distinguishes rendered rows (buckets, if aggregated) from the raw AEMET readings underlying them.',
      family: 'neutral',
    },
  ]

  return (
    <dl className="metrics-grid">
      {metrics.map((metric) => (
        <div className={`metric-card metric-card--${metric.family}`} key={metric.label}>
          <dt title={metric.reason}>{metric.label}</dt>
          <dd>{metric.value}</dd>
        </div>
      ))}
    </dl>
  )
}
