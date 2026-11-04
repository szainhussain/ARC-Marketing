import { useEffect, useRef } from 'react'

/**
 * Calls `load` on mount and then every `intervalMs` while `active` is true.
 * `load` receives an `isCancelled` check so late responses from an
 * unmounted/re-run effect never overwrite newer state (React 19 StrictMode
 * double-invokes mount effects — see CLAUDE.md frontend conventions).
 */
export function usePolling(
  load: (isCancelled: () => boolean) => Promise<void>,
  deps: unknown[],
  { intervalMs = 4000, active = true }: { intervalMs?: number; active?: boolean } = {},
) {
  const loadRef = useRef(load)
  loadRef.current = load

  useEffect(() => {
    let cancelled = false
    const isCancelled = () => cancelled
    loadRef.current(isCancelled).catch(() => undefined)
    if (!active) {
      return () => {
        cancelled = true
      }
    }
    const handle = window.setInterval(() => {
      if (document.visibilityState === 'visible') {
        loadRef.current(isCancelled).catch(() => undefined)
      }
    }, intervalMs)
    return () => {
      cancelled = true
      window.clearInterval(handle)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, active, intervalMs])
}
