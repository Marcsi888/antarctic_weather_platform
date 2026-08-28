import { useMemo } from 'react'
import { AGGREGATION_LEVELS, STATIONS } from '../constants/labels'
import type { ObservationQuery, ObservationResponse } from '../types/api'
import { summarize } from '../utils/statistics'

interface QuerySummaryProps {
  query: ObservationQuery
  data: readonly ObservationResponse[]
}

function labelFor<T extends string>(options: readonly { value: T; label: string }[], value: T): string {
  return options.find((o) => o.value === value)?.label ?? value
}

export function QuerySummary({ query, data }: QuerySummaryProps) {
  const summary = useMemo(() => summarize(data), [data])

  const measurementsLabel =
    query.measurements.length === 0 ? 'All' : query.measurements.join(', ')

  const timezoneLabel = query.timezone ?? 'Europe/Madrid (server default)'

  return (
    <dl className="query-summary">
      <div>
        <dt>Station</dt>
        <dd>{labelFor(STATIONS, query.station)}</dd>
      </div>
      <div>
        <dt>Aggregation</dt>
        <dd>{labelFor(AGGREGATION_LEVELS, query.aggregation)}</dd>
      </div>
      <div>
        <dt>Timezone</dt>
        <dd>{timezoneLabel}</dd>
      </div>
      <div>
        <dt>Measurements requested</dt>
        <dd>{measurementsLabel}</dd>
      </div>
      <div>
        <dt>Requested range</dt>
        <dd>
          {query.start} – {query.end}
        </dd>
      </div>
      <div>
        <dt>Returned period</dt>
        <dd>
          {summary.periodStart !== null && summary.periodEnd !== null
            ? `${summary.periodStart} – ${summary.periodEnd}`
            : '-'}
        </dd>
      </div>
      <div>
        <dt>Observations</dt>
        <dd>
          {data.length.toString()} rows / {summary.totalObservationCount.toString()} raw readings
        </dd>
      </div>
    </dl>
  )
}
