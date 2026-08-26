import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ObservationResponse } from '../types/api'
import { bucketWindSpeed } from '../utils/statistics'

interface WindDistributionChartProps {
  data: readonly ObservationResponse[]
}

// A time-series mean line answers "what's typical" but conceals
// variability: a sustained mean of 8 m/s could mean "always ~8 m/s"
// (bankable) or "half the time near-zero, half near 16" (not). This
// histogram re-projects the same already-fetched windSpeedMs values into
// a distribution, single axis, no invented data.
export function WindDistributionChart({ data }: WindDistributionChartProps) {
  const buckets = bucketWindSpeed(data)

  if (buckets.length === 0) {
    return (
      <p className="results-empty">
        No wind speed data available for this query to build a distribution from — try including
        wind speed in the requested measurements, or a different date range.
      </p>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={buckets} margin={{ top: 8, right: 24, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="rangeLabel" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
        <Tooltip
          formatter={(value: number | string | readonly (number | string)[] | undefined) => [
            typeof value === 'number' ? value : '—',
            'Observations',
          ]}
        />
        <Bar dataKey="count" name="Observations" fill="#2471a3" />
      </BarChart>
    </ResponsiveContainer>
  )
}
