// Abstract Antarctic landscape: layered ice-mountain silhouettes, faint
// topographic contour arcs, and a wind-flow motif, all vector, no
// photography, no raster gradients. Purely decorative alongside the two
// real station markers, which carry real (short) text labels rather than
// relying on position/color alone to identify which station is which.
function HeroLandscape() {
  return (
    <svg
      className="hero-landscape"
      viewBox="0 0 400 280"
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label="Abstract illustration of the Antarctic coastline showing the approximate positions of the Gabriel de Castilla and Juan Carlos I stations"
    >
      <g opacity="0.35" fill="none" stroke="var(--glacial-cyan)" strokeWidth="1">
        <path d="M -10 210 Q 80 180 160 205 T 410 195" />
        <path d="M -10 225 Q 90 198 170 222 T 410 212" />
        <path d="M -10 240 Q 100 218 180 238 T 410 230" />
      </g>
      <path
        d="M -10 260 L 60 160 L 110 210 L 170 120 L 230 200 L 290 150 L 350 215 L 410 175 L 410 280 L -10 280 Z"
        fill="var(--polar-mid)"
        opacity="0.55"
      />
      <path
        d="M -10 280 L 40 195 L 100 240 L 150 165 L 220 235 L 280 185 L 340 245 L 410 210 L 410 280 Z"
        fill="var(--glacial-cyan)"
        opacity="0.22"
      />
      <g stroke="var(--glacial-pale)" strokeWidth="1.4" fill="none" opacity="0.5" strokeLinecap="round">
        <path d="M 20 60 Q 60 50 90 62 T 160 58" />
        <path d="M 40 85 Q 85 72 120 88 T 200 80" />
        <path d="M 10 40 Q 45 32 70 42 T 130 36" />
      </g>
      <g transform="translate(150, 130)">
        <circle className="station-pin-ring" r="12" />
        <circle className="station-pin" r="4" />
        <text className="station-label" x="12" y="-10">
          Gabriel de Castilla
        </text>
      </g>
      <g transform="translate(255, 172)">
        <circle className="station-pin-ring" r="12" />
        <circle className="station-pin" r="4" />
        <text className="station-label" x="12" y="18">
          Juan Carlos I
        </text>
      </g>
    </svg>
  )
}

// Persists across loading/error/success: the same polar identity as the
// full Hero (gradient, eyebrow, product name) but without the landscape
// illustration, copy, CTA, or stat strip, so the page never goes headless
// once results are on screen, while staying quiet enough not to compete
// with the analytical workspace below it.
export function CompactHeader() {
  return (
    <header className="hero hero--compact">
      <div className="hero-grid hero-grid--compact">
        <div>
          <p className="hero-eyebrow">AEMET OpenData · Antarctic Stations</p>
          <h2 className="hero-compact-title">Antarctic Weather Platform</h2>
        </div>
      </div>
    </header>
  )
}

interface HeroProps {
  onStartQuery: () => void
}

export function Hero({ onStartQuery }: HeroProps) {
  return (
    <header className="hero">
      <div className="hero-grid">
        <div>
          <p className="hero-eyebrow">AEMET OpenData · Antarctic Stations</p>
          <h1>
            Reading the wind
            <br />
            at the edge of the map.
          </h1>
          <p className="hero-copy">
            Historical temperature, pressure, and wind observations from Spain&apos;s two
            Antarctic research stations, queried, cached, and analyzed for wind-farm
            feasibility.
          </p>
          <button type="button" className="hero-cta" onClick={onStartQuery}>
            Start a query ↓
          </button>
        </div>
        <div className="hero-visual">
          <HeroLandscape />
        </div>
      </div>

      <dl className="hero-stats">
        <div className="hero-stat">
          <dt className="hero-stat-label">Antarctic stations</dt>
          <dd className="hero-stat-value">2</dd>
        </div>
        <div className="hero-stat">
          <dt className="hero-stat-label">Meteorological variables</dt>
          <dd className="hero-stat-value">3</dd>
        </div>
        <div className="hero-stat">
          <dt className="hero-stat-label">Aggregation levels</dt>
          <dd className="hero-stat-value">4</dd>
        </div>
      </dl>
    </header>
  )
}
