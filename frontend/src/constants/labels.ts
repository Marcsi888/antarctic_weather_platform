import type { AggregationLevel, Station } from '../types/api'

export const STATIONS: readonly { value: Station; label: string }[] = [
  { value: 'gabriel_de_castilla', label: 'Gabriel de Castilla' },
  { value: 'juan_carlos_i', label: 'Juan Carlos I' },
]

export const AGGREGATION_LEVELS: readonly { value: AggregationLevel; label: string }[] = [
  { value: 'none', label: 'None' },
  { value: 'hourly', label: 'Hourly' },
  { value: 'daily', label: 'Daily' },
  { value: 'monthly', label: 'Monthly' },
]

// Curated, not exhaustive: the backend accepts any IANA timezone name or
// fixed UTC offset, so this list covers common cases fast while
// QueryForm's "Other" option keeps the full range reachable via free text.
export const COMMON_TIMEZONES: readonly { value: string; label: string }[] = [
  { value: 'Europe/Madrid', label: 'Europe/Madrid (default)' },
  { value: 'UTC', label: 'UTC' },
  { value: 'Europe/London', label: 'Europe/London' },
  { value: 'Europe/Berlin', label: 'Europe/Berlin' },
  { value: 'America/New_York', label: 'America/New York' },
  { value: 'America/Los_Angeles', label: 'America/Los Angeles' },
  { value: 'Asia/Tokyo', label: 'Asia/Tokyo' },
  { value: 'Australia/Sydney', label: 'Australia/Sydney' },
]

export const OTHER_TIMEZONE_OPTION = '__other__'
