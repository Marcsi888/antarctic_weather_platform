import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { QueryForm } from './QueryForm'

// A datetime-local input's .value omits seconds whenever they're :00,
// regardless of step="1" — confirmed both in jsdom (here) and in a real
// Chromium browser (manual check during development), so this is a real
// cross-environment behavior, not a jsdom-only quirk. The backend
// requires the full HH:MM:SS format and rejects a shortened value, so
// QueryForm pads it back on before storing/submitting (see
// withSeconds() in QueryForm.tsx). These tests assert the padded value
// that actually reaches onSubmit, since that's the contract that matters.
const PADDED_START = '2024-01-15T00:00:00'
const PADDED_END = '2024-01-15T06:00:00'

describe('QueryForm', () => {
  it('submits the query when start is before end', async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(<QueryForm onSubmit={onSubmit} disabled={false} />)

    await user.type(screen.getByLabelText('Start'), '2024-01-15T00:00:00')
    await user.type(screen.getByLabelText('End'), '2024-01-15T06:00:00')
    await user.click(screen.getByRole('button', { name: /query/i }))

    expect(onSubmit).toHaveBeenCalledOnce()
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        start: PADDED_START,
        end: PADDED_END,
      }),
    )
  })

  it('pads seconds back onto a value the browser reports without them', async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(<QueryForm onSubmit={onSubmit} disabled={false} />)

    // Typing without explicit seconds is exactly the case that
    // previously reached the backend as "...T00:00" and was rejected.
    await user.type(screen.getByLabelText('Start'), '2024-01-15T00:00')
    await user.type(screen.getByLabelText('End'), '2024-01-15T06:00')
    await user.click(screen.getByRole('button', { name: /query/i }))

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ start: PADDED_START, end: PADDED_END }),
    )
  })

  it('rejects submission and does not call onSubmit when required fields are empty', async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(<QueryForm onSubmit={onSubmit} disabled={false} />)

    await user.click(screen.getByRole('button', { name: /query/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Start and end datetime are required.',
    )
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('rejects submission when start is not before end', async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(<QueryForm onSubmit={onSubmit} disabled={false} />)

    await user.type(screen.getByLabelText('Start'), '2024-01-15T12:00:00')
    await user.type(screen.getByLabelText('End'), '2024-01-15T06:00:00')
    await user.click(screen.getByRole('button', { name: /query/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Start must be before end.')
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('omits timezone from the submitted query when the field is cleared', async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(<QueryForm onSubmit={onSubmit} disabled={false} />)

    await user.clear(screen.getByLabelText(/Timezone/))
    await user.type(screen.getByLabelText('Start'), '2024-01-15T00:00:00')
    await user.type(screen.getByLabelText('End'), '2024-01-15T06:00:00')
    await user.click(screen.getByRole('button', { name: /query/i }))

    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ timezone: undefined }))
  })

  it('sends an empty measurements array when none are checked', async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(<QueryForm onSubmit={onSubmit} disabled={false} />)

    await user.type(screen.getByLabelText('Start'), '2024-01-15T00:00:00')
    await user.type(screen.getByLabelText('End'), '2024-01-15T06:00:00')
    await user.click(screen.getByRole('button', { name: /query/i }))

    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ measurements: [] }))
  })

  it('toggles a measurement on and back off', async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(<QueryForm onSubmit={onSubmit} disabled={false} />)

    const pressureCheckbox = screen.getByLabelText('Pressure')
    await user.click(pressureCheckbox)
    expect(pressureCheckbox).toBeChecked()

    await user.click(pressureCheckbox)
    expect(pressureCheckbox).not.toBeChecked()
  })

  it('"All" is checked by default and unchecks automatically when a single measurement is picked', async () => {
    const user = userEvent.setup()
    render(<QueryForm onSubmit={vi.fn()} disabled={false} />)

    const allCheckbox = screen.getByLabelText('All')
    expect(allCheckbox).toBeChecked()

    await user.click(screen.getByLabelText('Temperature'))

    expect(allCheckbox).not.toBeChecked()
    expect(screen.getByLabelText('Temperature')).toBeChecked()
    expect(screen.getByLabelText('Pressure')).not.toBeChecked()
  })

  it('selecting a measurement while "All" is active replaces the selection, not adds to it', async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(<QueryForm onSubmit={onSubmit} disabled={false} />)

    await user.type(screen.getByLabelText('Start'), '2024-01-15T00:00:00')
    await user.type(screen.getByLabelText('End'), '2024-01-15T06:00:00')
    await user.click(screen.getByLabelText('Pressure'))
    await user.click(screen.getByRole('button', { name: /query/i }))

    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ measurements: ['pressure'] }))
  })

  it('picking a second measurement after the first adds to the selection', async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(<QueryForm onSubmit={onSubmit} disabled={false} />)

    await user.type(screen.getByLabelText('Start'), '2024-01-15T00:00:00')
    await user.type(screen.getByLabelText('End'), '2024-01-15T06:00:00')
    await user.click(screen.getByLabelText('Pressure'))
    await user.click(screen.getByLabelText('Wind speed'))
    await user.click(screen.getByRole('button', { name: /query/i }))

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ measurements: ['pressure', 'speed'] }),
    )
  })

  it('clicking "All" resets the selection back to empty', async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(<QueryForm onSubmit={onSubmit} disabled={false} />)

    await user.type(screen.getByLabelText('Start'), '2024-01-15T00:00:00')
    await user.type(screen.getByLabelText('End'), '2024-01-15T06:00:00')
    await user.click(screen.getByLabelText('Pressure'))
    await user.click(screen.getByLabelText('All'))
    await user.click(screen.getByRole('button', { name: /query/i }))

    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ measurements: [] }))
    expect(screen.getByLabelText('All')).toBeChecked()
  })

  it('unchecking the only selected measurement falls back to "All"', async () => {
    const user = userEvent.setup()
    render(<QueryForm onSubmit={vi.fn()} disabled={false} />)

    const pressureCheckbox = screen.getByLabelText('Pressure')
    await user.click(pressureCheckbox)
    await user.click(pressureCheckbox)

    expect(screen.getByLabelText('All')).toBeChecked()
  })

  it('disables all inputs and the submit button when disabled', () => {
    render(<QueryForm onSubmit={vi.fn()} disabled={true} />)

    expect(screen.getByLabelText('Station')).toBeDisabled()
    expect(screen.getByLabelText('Start')).toBeDisabled()
    expect(screen.getByLabelText('End')).toBeDisabled()
    expect(screen.getByRole('button', { name: /loading/i })).toBeDisabled()
  })
})
