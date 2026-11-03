const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000/api/v1'

export class ApiError extends Error {
  code: string
  details: { field: string; issue: string }[]
  status: number

  constructor(status: number, code: string, message: string, details: { field: string; issue: string }[]) {
    super(message)
    this.status = status
    this.code = code
    this.details = details
  }
}

let cachedCsrfToken: string | null = null

async function getCsrfToken(): Promise<string> {
  if (cachedCsrfToken) return cachedCsrfToken
  const res = await fetch(`${API_BASE_URL}/auth/csrf-token`, { credentials: 'include' })
  const data = await res.json()
  cachedCsrfToken = data.csrf_token
  return cachedCsrfToken as string
}

export function clearCsrfTokenCache() {
  cachedCsrfToken = null
}

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  idempotencyKey?: string
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method || 'GET'
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }

  if (method !== 'GET') {
    headers['X-CSRFToken'] = await getCsrfToken()
  }
  if (options.idempotencyKey) {
    headers['Idempotency-Key'] = options.idempotencyKey
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    credentials: 'include',
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  })

  if (res.status === 204) return undefined as T

  const data = await res.json().catch(() => ({}))

  if (!res.ok) {
    const err = data?.error || {}
    throw new ApiError(res.status, err.code || 'UNKNOWN_ERROR', err.message || 'Request failed.', err.details || [])
  }

  return data as T
}
