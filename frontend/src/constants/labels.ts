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
