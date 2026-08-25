import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// React Testing Library's auto-cleanup relies on Vitest's global afterEach
// hook (globals: true); this project keeps globals: false deliberately
// (see vite.config.ts), so cleanup is registered explicitly here instead
// — without it, each test's render() adds another copy of the tree to
// the same document rather than replacing the previous test's.
afterEach(() => {
  cleanup()
})
