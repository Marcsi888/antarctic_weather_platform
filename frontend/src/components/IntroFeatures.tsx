import type { ReactNode } from 'react'

interface IntroCard {
  family: 'wind' | 'temp' | 'pressure'
  title: string
  description: string
  icon: ReactNode
}

const CARDS: readonly IntroCard[] = [
  {
    family: 'wind',
    title: 'Wind Speed',
    description:
      'Mean and peak wind speed over time, plus a distribution view showing how variable conditions really are.',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <path d="M3 8h11a3 3 0 1 0-3-3M3 16h15a3 3 0 1 1-3 3M3 12h9" />
      </svg>
    ),
  },
  {
    family: 'temp',
    title: 'Temperature',
    description:
      'Hourly, daily, or monthly temperature trends, timezone-correct across daylight-saving transitions.',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <path d="M14 4v10.5a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z" />
      </svg>
    ),
  },
  {
    family: 'pressure',
    title: 'Atmospheric Pressure',
    description:
      'Barometric trends alongside wind and temperature, aggregated to the level you choose.',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 3" />
      </svg>
    ),
  },
]

const FLOW_STEPS: readonly string[] = [
  'AEMET OpenData',
  'Validation & Transformation',
  'SQLite Cache',
  'FastAPI',
  'Analytics UI',
]

// Shown only before the first query: a short explanation of what each of
// the three measurements offers, plus the real data pipeline. Not present
// once a query succeeds, since the actual dashboard sections
// (SummaryMetrics, ObservationsChart, WindEnergyView) take over that role
// with real data.
export function IntroFeatures() {
  return (
    <div className="intro-features">
      <div className="intro-cards">
        {CARDS.map((card) => (
          <div className={`intro-card intro-card--${card.family}`} key={card.family}>
            <div className="intro-card-icon">{card.icon}</div>
            <h3>{card.title}</h3>
            <p>{card.description}</p>
          </div>
        ))}
      </div>

      <p className="flow-strip" aria-label="Data pipeline">
        {FLOW_STEPS.map((step, index) => (
          <span key={step}>
            <span className="flow-node">{step}</span>
            {index < FLOW_STEPS.length - 1 && (
              <span className="flow-arrow" aria-hidden="true">
                {' '}
                →{' '}
              </span>
            )}
          </span>
        ))}
      </p>
    </div>
  )
}
