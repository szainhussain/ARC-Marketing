import { useCallback, useEffect, useRef, useState } from 'react'
import { apiRequest, ApiError } from '../api/client'

/**
 * GET a resource with loading/error state and the cancellation guard
 * required by CLAUDE.md (React 19 StrictMode double-invokes effects).
 * `path` null = don't fetch yet. Optional polling while `pollMs` is set.
 */
export function useResource<T>(path: string | null, { pollMs }: { pollMs?: number } = {}) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState<boolean>(!!path)
  const generation = useRef(0)

  const load = useCallback(async () => {
    if (!path) return
    const mine = ++generation.current
    try {
      const result = await apiRequest<T>(path)
      if (mine !== generation.current) return
      setData(result)
      setError(null)
    } catch (err) {
      if (mine !== generation.current) return
      setError(err instanceof ApiError ? err.message : 'Something went wrong loading this page.')
    } finally {
      if (mine === generation.current) setLoading(false)
    }
  }, [path])

  useEffect(() => {
    setLoading(!!path)
    load()
    if (!pollMs || !path) {
      return () => {
        generation.current++
      }
    }
    const handle = window.setInterval(() => {
      if (document.visibilityState === 'visible') load()
    }, pollMs)
    return () => {
      generation.current++
      window.clearInterval(handle)
    }
  }, [load, path, pollMs])

  return { data, error, loading, reload: load, setData }
}

/** Run a mutation with busy + error state. */
export function useAction() {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const run = useCallback(async <R,>(fn: () => Promise<R>): Promise<R | undefined> => {
    setBusy(true)
    setError(null)
    try {
      return await fn()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'That action failed.')
      return undefined
    } finally {
      setBusy(false)
    }
  }, [])
  return { busy, error, setError, run }
}
