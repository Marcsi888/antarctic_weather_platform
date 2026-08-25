import { useId, useState } from 'react'
import type { SubmitEvent } from 'react'
import type { AggregationLevel, Measurement, ObservationQuery, Station } from '../types/api'

interface QueryFormProps {
  // Accepts a sync or async handler explicitly, rather than declaring
  // void and letting an async caller violate the stated contract: App's
  // handleSubmit performs the actual network request and already
  // handles rejections internally via try/catch.
  onSubmit: (query: ObservationQuery) => void | Promise<void>
  disabled: boolean
}

const STATIONS: readonly { value: Station; label: string }[] = [
  { value: 'gabriel_de_castilla', label: 'Gabriel de Castilla' },
  { value: 'juan_carlos_i', label: 'Juan Carlos I' },
]

const AGGREGATION_LEVELS: readonly { value: AggregationLevel; label: string }[] = [
  { value: 'none', label: 'None' },
  { value: 'hourly', label: 'Hourly' },
  { value: 'daily', label: 'Daily' },
  { value: 'monthly', label: 'Monthly' },
]

const MEASUREMENTS: readonly { value: Measurement; label: string }[] = [
  { value: 'temperature', label: 'Temperature' },
  { value: 'pressure', label: 'Pressure' },
  { value: 'speed', label: 'Wind speed' },
]

// Browser timezone as an editable convenience default, not a geolocation
// lookup: Intl reads a setting already on the device, no network request
// or IP involved. Falls back to Europe/Madrid (the backend's own default)
// if the browser can't report one, or reports something the backend's
// zoneinfo/fixed-offset parser wouldn't recognize as a plausible IANA name.
function detectBrowserTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone
  } catch {
    return 'Europe/Madrid'
  }
}

function validate(start: string, end: string): string | null {
  if (!start || !end) {
    return 'Start and end datetime are required.'
  }
  if (start >= end) {
    return 'Start must be before end.'
  }
  return null
}

export function QueryForm({ onSubmit, disabled }: QueryFormProps) {
  const formId = useId()
  const [station, setStation] = useState<Station>('gabriel_de_castilla')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [timezone, setTimezone] = useState(detectBrowserTimezone)
  const [aggregation, setAggregation] = useState<AggregationLevel>('none')
  const [measurements, setMeasurements] = useState<readonly Measurement[]>([])
  const [validationError, setValidationError] = useState<string | null>(null)

  function toggleMeasurement(value: Measurement) {
    setMeasurements((current) =>
      current.includes(value) ? current.filter((m) => m !== value) : [...current, value],
    )
  }

  function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
    const error = validate(start, end)
    setValidationError(error)
    if (error) {
      return
    }
    // App.handleSubmit already handles its own rejections via try/catch;
    // this callback's return value is deliberately not awaited here.
    void onSubmit({
      station,
      start,
      end,
      timezone: timezone.trim() ? timezone.trim() : undefined,
      aggregation,
      measurements,
    })
  }

  return (
    <form onSubmit={handleSubmit} aria-label="Weather observation query" noValidate>
      <div>
        <label htmlFor={`${formId}-station`}>Station</label>
        <select
          id={`${formId}-station`}
          value={station}
          onChange={(e) => {
            setStation(e.target.value as Station)
          }}
          disabled={disabled}
        >
          {STATIONS.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor={`${formId}-start`}>Start</label>
        <input
          id={`${formId}-start`}
          type="datetime-local"
          step={1}
          value={start}
          onChange={(e) => {
            setStart(e.target.value)
          }}
          disabled={disabled}
          required
        />
      </div>

      <div>
        <label htmlFor={`${formId}-end`}>End</label>
        <input
          id={`${formId}-end`}
          type="datetime-local"
          step={1}
          value={end}
          onChange={(e) => {
            setEnd(e.target.value)
          }}
          disabled={disabled}
          required
        />
      </div>

      <div>
        <label htmlFor={`${formId}-timezone`}>
          Timezone <span>(IANA name or UTC offset, e.g. +02:00)</span>
        </label>
        <input
          id={`${formId}-timezone`}
          type="text"
          value={timezone}
          onChange={(e) => {
            setTimezone(e.target.value)
          }}
          disabled={disabled}
          placeholder="Europe/Madrid"
        />
      </div>

      <div>
        <label htmlFor={`${formId}-aggregation`}>Aggregation</label>
        <select
          id={`${formId}-aggregation`}
          value={aggregation}
          onChange={(e) => {
            setAggregation(e.target.value as AggregationLevel)
          }}
          disabled={disabled}
        >
          {AGGREGATION_LEVELS.map((a) => (
            <option key={a.value} value={a.value}>
              {a.label}
            </option>
          ))}
        </select>
      </div>

      <fieldset disabled={disabled}>
        <legend>Measurements (none selected returns all)</legend>
        {MEASUREMENTS.map((m) => (
          <label key={m.value}>
            <input
              type="checkbox"
              checked={measurements.includes(m.value)}
              onChange={() => {
                toggleMeasurement(m.value)
              }}
            />
            {m.label}
          </label>
        ))}
      </fieldset>

      {validationError && <p role="alert">{validationError}</p>}

      <button type="submit" disabled={disabled}>
        {disabled ? 'Loading…' : 'Query'}
      </button>
    </form>
  )
}
