import { useEffect, useId, useState } from 'react'
import type { SubmitEvent } from 'react'
import { getLatestAvailableDate } from '../api/client'
import {
  AGGREGATION_LEVELS,
  COMMON_TIMEZONES,
  OTHER_TIMEZONE_OPTION,
  STATIONS,
} from '../constants/labels'
import type { AggregationLevel, Measurement, ObservationQuery, Station } from '../types/api'

interface QueryFormProps {
  // Accepts a sync or async handler explicitly, rather than declaring
  // void and letting an async caller violate the stated contract: App's
  // handleSubmit performs the actual network request and already
  // handles rejections internally via try/catch.
  onSubmit: (query: ObservationQuery) => void | Promise<void>
  disabled: boolean
}

const MEASUREMENTS: readonly { value: Measurement; label: string; family: string }[] = [
  { value: 'temperature', label: 'Temperature', family: 'temp' },
  { value: 'pressure', label: 'Pressure', family: 'pressure' },
  { value: 'speed', label: 'Wind speed', family: 'wind' },
]

// A datetime-local input's .value omits seconds whenever they're :00,
// even with step={1} set (a real browser behavior, not just a jsdom
// quirk), e.g. "2024-01-15T00:00" instead of "2024-01-15T00:00:00".
// The backend requires the full HH:MM:SS format and rejects the
// shortened string outright, so it must be padded before it's ever
// stored in state or sent.
function withSeconds(value: string): string {
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value) ? `${value}:00` : value
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
  const [timezoneSelection, setTimezoneSelection] = useState('Europe/Madrid')
  const [customTimezone, setCustomTimezone] = useState('')
  const [aggregation, setAggregation] = useState<AggregationLevel>('none')
  const [measurements, setMeasurements] = useState<readonly Measurement[]>([])
  const [validationError, setValidationError] = useState<string | null>(null)
  const [latestAvailableDate, setLatestAvailableDate] = useState<string | null>(null)

  // Genuine synchronization with an external system (what AEMET actually
  // has data for), not state derivable from props/other state: a real
  // useEffect case. Re-fetches on station change since availability is
  // scoped per station. Fails open: a failed/slow fetch just leaves both
  // fields unrestricted rather than blocking the form, since the
  // backend's own empty-result handling already covers a doomed query.
  useEffect(() => {
    let cancelled = false
    // getLatestAvailableDate itself never rejects (it fails open to null
    // internally); .catch() here is defense-in-depth so a violation of
    // that contract still can't crash the form or surface as an
    // unhandled rejection.
    void getLatestAvailableDate(station)
      .then((date) => {
        if (!cancelled) {
          setLatestAvailableDate(date)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setLatestAvailableDate(null)
        }
      })
    // On station change, the effect cleanup marks the in-flight request
    // for the previous station stale before the next one starts. The
    // stale max is left in place until the new station's real answer
    // arrives, rather than eagerly cleared (which would call setState
    // synchronously inside the effect body).
    return () => {
      cancelled = true
    }
  }, [station])

  // Both Start and End are capped at the same datetime: neither field
  // should let a user pick beyond what AEMET is confirmed to have data
  // for. A Start date past the data edge is just as doomed as an End
  // date past it.
  const maxAvailableDatetime =
    latestAvailableDate !== null ? `${latestAvailableDate}T23:59:59` : undefined

  // The dropdown covers common zones; "Other" reveals the free-text input
  // so the backend's full IANA-name/fixed-offset support stays reachable
  // without cluttering the dropdown with an exhaustive ~400-zone list.
  const isCustomTimezone = timezoneSelection === OTHER_TIMEZONE_OPTION
  const effectiveTimezone = isCustomTimezone ? customTimezone.trim() : timezoneSelection

  // An empty selection means "all" to the backend (see ObservationQuery),
  // so "All" is a UI-only concept: checked exactly when the selection is
  // empty. Picking an individual measurement while "All" is active
  // replaces the selection with just that one, rather than adding to an
  // implicit "everything" set; picking further ones then adds normally.
  // Unchecking the last individual measurement falls back to "All"
  // instead of leaving nothing selected, since an empty selection already
  // means the same thing.
  function selectAll() {
    setMeasurements([])
  }

  function toggleMeasurement(value: Measurement) {
    setMeasurements((current) =>
      current.length === 0
        ? [value]
        : current.includes(value)
          ? current.filter((m) => m !== value)
          : [...current, value],
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
      timezone: effectiveTimezone ? effectiveTimezone : undefined,
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
          max={maxAvailableDatetime}
          onChange={(e) => {
            setStart(withSeconds(e.target.value))
          }}
          disabled={disabled}
          required
        />
        {latestAvailableDate !== null && (
          <p className="field-hint">Data available through {latestAvailableDate}</p>
        )}
      </div>

      <div>
        <label htmlFor={`${formId}-end`}>End</label>
        <input
          id={`${formId}-end`}
          type="datetime-local"
          step={1}
          value={end}
          max={maxAvailableDatetime}
          onChange={(e) => {
            setEnd(withSeconds(e.target.value))
          }}
          disabled={disabled}
          required
        />
        {latestAvailableDate !== null && (
          <p className="field-hint">Data available through {latestAvailableDate}</p>
        )}
      </div>

      <div>
        <label htmlFor={`${formId}-timezone`}>Timezone</label>
        <select
          id={`${formId}-timezone`}
          value={timezoneSelection}
          onChange={(e) => {
            setTimezoneSelection(e.target.value)
          }}
          disabled={disabled}
        >
          {COMMON_TIMEZONES.map((tz) => (
            <option key={tz.value} value={tz.value}>
              {tz.label}
            </option>
          ))}
          <option value={OTHER_TIMEZONE_OPTION}>Other (enter manually)</option>
        </select>
        {isCustomTimezone && (
          <input
            id={`${formId}-timezone-custom`}
            type="text"
            aria-label="Custom timezone"
            value={customTimezone}
            onChange={(e) => {
              setCustomTimezone(e.target.value)
            }}
            disabled={disabled}
            placeholder="IANA name or UTC offset, e.g. +02:00"
          />
        )}
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
        <legend>Measurements</legend>
        <div>
          <label>
            <input type="checkbox" checked={measurements.length === 0} onChange={selectAll} />
            All
          </label>
          {MEASUREMENTS.map((m) => (
            <label key={m.value}>
              <input
                type="checkbox"
                checked={measurements.includes(m.value)}
                onChange={() => {
                  toggleMeasurement(m.value)
                }}
              />
              <span className={`measurement-swatch measurement-swatch--${m.family}`} aria-hidden="true" />
              {m.label}
            </label>
          ))}
        </div>
      </fieldset>

      {validationError && <p role="alert">{validationError}</p>}

      <button type="submit" disabled={disabled}>
        {disabled ? 'Loading…' : 'Query'}
      </button>
    </form>
  )
}
