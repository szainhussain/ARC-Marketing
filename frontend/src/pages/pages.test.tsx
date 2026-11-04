import { afterEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ContactPage } from './public/InfoPages'
import { SignupPage } from './public/AuthPages'
import { AuthProvider } from '../context/AuthContext'

function mockFetch(handler: (url: string, init?: RequestInit) => unknown) {
  const fn = vi.fn(async (url: string, init?: RequestInit) => {
    const body = handler(String(url), init)
    const status = (body as { __status?: number })?.__status || 200
    return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
  })
  vi.stubGlobal('fetch', fn)
  return fn
}

afterEach(() => vi.unstubAllGlobals())

describe('Contact form', () => {
  it('validates before sending, then submits', async () => {
    const fetchFn = mockFetch((url) => (url.includes('csrf') ? { csrf_token: 't' } : { status: 'received' }))
    render(<MemoryRouter><ContactPage /></MemoryRouter>)
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }))
    expect(screen.getAllByText('Required').length).toBe(1)
    expect(screen.getByText('A valid email is required')).toBeTruthy()
    expect(fetchFn).not.toHaveBeenCalled()

    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Sam' } })
    fireEvent.change(screen.getByLabelText('Work email'), { target: { value: 'sam@example.com' } })
    fireEvent.change(screen.getByLabelText('Message'), { target: { value: 'Tell me about pricing please' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }))
    await waitFor(() => expect(screen.getByText(/your message was received/)).toBeTruthy())
  })
})

describe('Signup form', () => {
  it('shows field errors without calling the API', () => {
    const fetchFn = mockFetch(() => ({ __status: 401, error: { code: 'AUTHENTICATION_ERROR', message: 'x' } }))
    render(<MemoryRouter><AuthProvider><SignupPage /></AuthProvider></MemoryRouter>)
    const callsBefore = fetchFn.mock.calls.length // AuthProvider's /me check
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }))
    expect(screen.getByText('Must be at least 8 characters')).toBeTruthy()
    expect(fetchFn.mock.calls.length).toBe(callsBefore)
  })
})
