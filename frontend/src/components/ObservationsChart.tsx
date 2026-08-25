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
    return '—'
  }
  if (typeof value === 'number') {
    return value.toFixed(1)
  }
  if (typeof value === 'string') {
    return value
  }
  return value.join(', ')
}

// Pressure (~950-1050 hPa) shares no meaningful scale with temperature
// (roughly -20 to 10 °C here) or wind speed (0-30 m/s): plotting all
// three against one Y-axis would flatten the smaller-magnitude series
// into visual noise. Pressure gets its own axis; temperature and wind
// speed share the other, since their magnitudes are closer to comparable.
//
// Lines are not connectNulls: a null value (a bucket with no valid
// readings, or a measurement not requested) is a real absence, not an
// interpolation opportunity — the same reasoning behind the backend
// reporting null rather than 0.0 for an all-bad-quality bucket.
export function ObservationsChart({ data }: ObservationsChartProps) {
  const hasTemperature = data.some((d) => d.temperatureCelsius !== null)
  const hasPressure = data.some((d) => d.pressureHpa !== null)
  const hasWindSpeed = data.some((d) => d.windSpeedMs !== null)

  if (data.length === 0 || (!hasTemperature && !hasPressure && !hasWindSpeed)) {
    return null
  }

  return (
    <ResponsiveContainer width="100%" height={360}>
      <LineChart data={data} margin={{ top: 8, right: 24, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="datetime" tick={{ fontSize: 11 }} minTickGap={40} />
        <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
        <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
        <Tooltip formatter={formatTooltipValue} />
        <Legend />
        {hasTemperature && (
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="temperatureCelsius"
            name="Temperature (°C)"
            stroke="#c0392b"
            dot={false}
          />
        )}
        {hasWindSpeed && (
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="windSpeedMs"
            name="Wind speed (m/s)"
            stroke="#2471a3"
            dot={false}
          />
        )}
        {hasPressure && (
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="pressureHpa"
            name="Pressure (hPa)"
            stroke="#7d3c98"
            dot={false}
          />
        )}
      </LineChart>
    </ResponsiveContainer>
  )
}
