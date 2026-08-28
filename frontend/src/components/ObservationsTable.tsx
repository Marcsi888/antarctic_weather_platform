import type { ObservationResponse } from '../types/api'

interface ObservationsTableProps {
  data: readonly ObservationResponse[]
}

function formatNumber(value: number | null, unit: string): string {
  return value === null ? '-' : `${value.toFixed(1)} ${unit}`
}

export function ObservationsTable({ data }: ObservationsTableProps) {
  if (data.length === 0) {
    return (
      <p className="results-empty">
        No observations for this query. AEMET's Antarctic dataset lags the present by several
        months, so very recent or future date ranges typically have no data yet. Try an earlier
        end date.
      </p>
    )
  }

  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th scope="col">Datetime</th>
            <th scope="col">Temperature</th>
            <th scope="col">Pressure</th>
            <th scope="col">Wind speed</th>
            <th scope="col">Wind speed (max)</th>
            <th scope="col">Readings</th>
          </tr>
        </thead>
        <tbody>
          {data.map((observation) => (
            <tr key={observation.datetime}>
              <td>{observation.datetime}</td>
              <td>{formatNumber(observation.temperatureCelsius, '°C')}</td>
              <td>{formatNumber(observation.pressureHpa, 'hPa')}</td>
              <td>{formatNumber(observation.windSpeedMs, 'm/s')}</td>
              <td>{formatNumber(observation.windSpeedMaxMs, 'm/s')}</td>
              <td>{observation.observationCount}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
