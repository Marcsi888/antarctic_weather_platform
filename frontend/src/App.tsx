import { useState } from 'react'
import { ApiError, getObservations } from './api/client'
import { ObservationsChart } from './components/ObservationsChart'
import { ObservationsTable } from './components/ObservationsTable'
import { QueryForm } from './components/QueryForm'
import { QuerySummary } from './components/QuerySummary'
import { SummaryMetrics } from './components/SummaryMetrics'
import { WindEnergyView } from './components/WindEnergyView'
import type { ObservationQuery } from './types/api'
import type { RequestState } from './types/requestState'

export default function App() {
  const [requestState, setRequestState] = useState<RequestState>({ status: 'idle' })
  // Only needed for QuerySummary: station/timezone/aggregation aren't
  // echoed back in ObservationResponse, so the as-submitted query is the
  // only source for them. Everything else shown in the UI is derived
  // from requestState.data itself, not duplicated into separate state.
  const [lastSubmittedQuery, setLastSubmittedQuery] = useState<ObservationQuery | null>(null)

  async function handleSubmit(query: ObservationQuery) {
    setRequestState({ status: 'loading' })
    setLastSubmittedQuery(query)
    try {
      const data = await getObservations(query)
      setRequestState({ status: 'success', data })
    } catch (error) {
      setRequestState({
        status: 'error',
        error: error instanceof ApiError ? error : new ApiError(0, 'Unexpected error.'),
      })
    }
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Antarctic Weather Platform</h1>
        <p>
          Historical weather observations from AEMET OpenData for the Gabriel de Castilla and
          Juan Carlos I Antarctic stations.
        </p>
      </header>

      <section aria-label="Query parameters" className="filter-bar">
        <QueryForm onSubmit={handleSubmit} disabled={requestState.status === 'loading'} />
      </section>

      <main>
        {requestState.status === 'idle' && (
          <section>
            <p className="results-idle">Submit a query to see observations.</p>
          </section>
        )}

        {requestState.status === 'loading' && (
          <section>
            <p role="status">Loading observations…</p>
          </section>
        )}

        {requestState.status === 'error' && (
          <section>
            <p role="alert">
              {requestState.error.status === 0
                ? requestState.error.message
                : `Request failed: ${requestState.error.message}`}
            </p>
          </section>
        )}

        {requestState.status === 'success' && lastSubmittedQuery && (
          <>
            <section aria-label="Query summary">
              <h2>Query summary</h2>
              <QuerySummary query={lastSubmittedQuery} data={requestState.data} />
            </section>

            <section aria-label="Summary metrics">
              <h2>Key statistics</h2>
              <SummaryMetrics data={requestState.data} />
            </section>

            <section aria-label="Wind energy analysis">
              <h2>Wind energy analysis</h2>
              <WindEnergyView data={requestState.data} />
            </section>

            <section aria-label="Time series">
              <h2>Time series</h2>
              <ObservationsChart data={requestState.data} />
            </section>

            <section aria-label="Observations table">
              <h2>Weather observations</h2>
              <ObservationsTable data={requestState.data} />
            </section>
          </>
        )}
      </main>
    </div>
  )
}
