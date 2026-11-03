import { useEffect, useRef, useState } from 'react'
import { useReducedMotion } from 'motion/react'

/**
 * Counts up to `value` once on mount. Skips the animation entirely under
 * prefers-reduced-motion (renders the final value immediately).
 */
export default function AnimatedNumber({
  value,
  format = (n: number) => String(Math.round(n)),
  durationMs = 900,
}: {
  value: number
  format?: (n: number) => string
  durationMs?: number
}) {
  const reduceMotion = useReducedMotion()
  const [display, setDisplay] = useState(reduceMotion ? value : 0)
  const frameRef = useRef<number | undefined>(undefined)

  useEffect(() => {
    if (reduceMotion) {
      setDisplay(value)
      return
    }
    const start = performance.now()
    const from = 0

    function tick(now: number) {
      const progress = Math.min((now - start) / durationMs, 1)
      const eased = 1 - Math.pow(1 - progress, 3) // ease-out cubic
      setDisplay(from + (value - from) * eased)
      if (progress < 1) {
        frameRef.current = requestAnimationFrame(tick)
      }
    }
    frameRef.current = requestAnimationFrame(tick)
    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value])

  return <>{format(display)}</>
}
