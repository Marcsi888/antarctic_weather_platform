import type { ApiError } from '../api/client'
import type { ObservationResponse } from './api'

// A discriminated union, not several independent booleans (isLoading,
// hasError, hasData...): those can drift into states that shouldn't be
// possible (loading and error simultaneously), and every read site would
// need to remember the right combination to check. Here, narrowing on
// `status` is enough for TypeScript to know which other fields exist.
export type RequestState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: readonly ObservationResponse[] }
  | { status: 'error'; error: ApiError }
