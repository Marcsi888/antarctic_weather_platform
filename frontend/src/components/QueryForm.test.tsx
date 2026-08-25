import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { QueryForm } from './QueryForm'

// jsdom's datetime-local input does not honor step="1" for typed keyboard
// input the way a real browser does: user.type() with a full HH:MM:SS
// value still yields an HH:MM value (seconds truncated), regardless of
// the step attribute. Verified directly against this component; this is
// a jsdom limitation, not app behavior — a real browser (confirmed via a
// manual headless Chromium check during development) produces the full
// YYYY-MM-DDTHH:MM:SS value the backend requires. Tests here assert
// against what jsdom actually produces so failures reflect real
// regressions, not environment noise.
const JSDOM_DATETIME_LOCAL_START = '2024-01-15T00:00'
const JSDOM_DATETIME_LOCAL_END = '2024-01-15T06:00'

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
        start: JSDOM_DATETIME_LOCAL_START,
        end: JSDOM_DATETIME_LOCAL_END,
      }),
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

  it('disables all inputs and the submit button when disabled', () => {
    render(<QueryForm onSubmit={vi.fn()} disabled={true} />)

    expect(screen.getByLabelText('Station')).toBeDisabled()
    expect(screen.getByLabelText('Start')).toBeDisabled()
    expect(screen.getByLabelText('End')).toBeDisabled()
    expect(screen.getByRole('button', { name: /loading/i })).toBeDisabled()
  })
})
