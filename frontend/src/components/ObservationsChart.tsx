import type { ReactNode } from 'react'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { ObservationResponse } from '../types/api'

interface ObservationsChartProps {
  data: readonly ObservationResponse[]
}

// Recharts' default tooltip renders raw numeric values with full
// floating-point precision (a mean over n readings is rarely a round
// number). Matches ObservationsTable's own formatting convention so the
// chart and table agree on how a value is displayed. Arrays only occur
// for range-style series (e.g. Area charts), which this chart does not
// use; included for type-correctness against Recharts' general Formatter
// signature, not because it is reachable here.
function formatTooltipValue(
  value: number | string | readonly (number | string)[] | undefined,
): string {
  if (value === undefined) {
    return '-'
  }
  if (typeof value === 'number') {
    return value.toFixed(1)
  }
  if (typeof value === 'string') {
    return value
  }
  return value.join(', ')
}

const SYNC_ID = 'observations-timeseries'

interface SeriesPanelProps {
  data: readonly ObservationResponse[]
  title: string
  children: ReactNode
}

// One axis per panel, not a dual-axis chart: two independently-scaled
// Y-axes make it look as though their line shapes are comparable, which
// is an artifact of arbitrary axis scaling, not a real relationship in
// the data. Three synced single-axis panels (shared syncId) keep every
// series honest while still giving a shared crosshair/tooltip across all
// three on hover.
function SeriesPanel({ data, title, children }: SeriesPanelProps) {
  return (
    <div className="chart-panel">
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={160}>
        <LineChart syncId={SYNC_ID} data={data} margin={{ top: 8, right: 24, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="datetime" tick={{ fontSize: 11 }} minTickGap={40} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip formatter={formatTooltipValue} />
          <Legend />
          {children}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

// Lines are not connectNulls: a null value (a bucket with no valid
// readings, or a measurement not requested) is a real absence, not an
// interpolation opportunity, the same reasoning behind the backend
// reporting null rather than 0.0 for an all-bad-quality bucket.
export function ObservationsChart({ data }: ObservationsChartProps) {
  const hasTemperature = data.some((d) => d.temperatureCelsius !== null)
  const hasPressure = data.some((d) => d.pressureHpa !== null)
  const hasWindSpeed = data.some((d) => d.windSpeedMs !== null)
  const hasWindSpeedMax = data.some((d) => d.windSpeedMaxMs !== null)

  if (data.length === 0 || (!hasTemperature && !hasPressure && !hasWindSpeed && !hasWindSpeedMax)) {
    return null
  }

  return (
    <div className="chart-panels">
      {hasTemperature && (
        <SeriesPanel data={data} title="Temperature (°C)">
          <Line
            type="monotone"
            dataKey="temperatureCelsius"
            name="Temperature (°C)"
            stroke="var(--temp)"
            dot={false}
          />
        </SeriesPanel>
      )}
      {(hasWindSpeed || hasWindSpeedMax) && (
        <SeriesPanel data={data} title="Wind speed (m/s)">
          {hasWindSpeed && (
            <Line
              type="monotone"
              dataKey="windSpeedMs"
              name="Wind speed, mean (m/s)"
              stroke="var(--wind)"
              dot={false}
            />
          )}
          {hasWindSpeedMax && (
            <Line
              type="monotone"
              dataKey="windSpeedMaxMs"
              name="Wind speed, max (m/s)"
              stroke="var(--wind)"
              strokeOpacity={0.55}
              strokeDasharray="4 3"
              dot={false}
            />
          )}
        </SeriesPanel>
      )}
      {hasPressure && (
        <SeriesPanel data={data} title="Pressure (hPa)">
          <Line
            type="monotone"
            dataKey="pressureHpa"
            name="Pressure (hPa)"
            stroke="var(--pressure)"
            dot={false}
          />
        </SeriesPanel>
      )}
    </div>
  )
}
