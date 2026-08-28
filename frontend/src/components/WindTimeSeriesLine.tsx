import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ObservationResponse } from '../types/api'

interface WindTimeSeriesLineProps {
  data: readonly ObservationResponse[]
}

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

// Standalone (not part of ObservationsChart's synced group): this chart
// is composed inside WindEnergyView, a separate analytical context from
// the general time-series view, so it does not need to share a syncId
// with temperature/pressure panels it isn't shown alongside.
export function WindTimeSeriesLine({ data }: WindTimeSeriesLineProps) {
  const hasWindSpeed = data.some((d) => d.windSpeedMs !== null)
  const hasWindSpeedMax = data.some((d) => d.windSpeedMaxMs !== null)

  if (!hasWindSpeed && !hasWindSpeedMax) {
    return null
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data} margin={{ top: 8, right: 24, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="datetime" tick={{ fontSize: 11 }} minTickGap={40} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip formatter={formatTooltipValue} />
        <Legend />
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
      </LineChart>
    </ResponsiveContainer>
  )
}
