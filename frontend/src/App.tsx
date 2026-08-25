import { useState } from 'react'
import { ApiError, getObservations } from './api/client'
import { ObservationsChart } from './components/ObservationsChart'
import { ObservationsTable } from './components/ObservationsTable'
import { QueryForm } from './components/QueryForm'
import type { ObservationQuery } from './types/api'
import type { RequestState } from './types/requestState'

export default function App() {
  const [requestState, setRequestState] = useState<RequestState>({ status: 'idle' })

  async function handleSubmit(query: ObservationQuery) {
    setRequestState({ status: 'loading' })
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
    <main>
      <header>
        <h1>Antarctic Weather Platform</h1>
        <p>
          Historical weather observations from AEMET OpenData for the Gabriel de Castilla and
          Juan Carlos I Antarctic stations.
        </p>
      </header>

      <section aria-label="Query parameters">
        <QueryForm onSubmit={handleSubmit} disabled={requestState.status === 'loading'} />
      </section>

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

      {requestState.status === 'success' && (
        <section aria-label="Results">
          <ObservationsChart data={requestState.data} />
          <ObservationsTable data={requestState.data} />
        </section>
      )}
    </main>
  )
}
