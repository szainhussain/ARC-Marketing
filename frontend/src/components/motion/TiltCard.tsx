import { useRef, type ReactNode } from 'react'

/**
 * Lightweight 3D tilt-on-hover, driven by CSS custom properties
 * (--rx/--ry, consumed by the .tilt-card class in index.css) rather than
 * animating transform directly in JS, so the actual motion still goes
 * through CSS transitions (and respects prefers-reduced-motion via the
 * existing global guard, see index.css's .tilt-card media query).
 * No mouse tracking at all on touch devices (no hover capability).
 */
export default function TiltCard({
  children,
  className = '',
  maxTilt = 6,
}: {
  children: ReactNode
  className?: string
  maxTilt?: number
}) {
  const ref = useRef<HTMLDivElement>(null)

  function handleMouseMove(e: React.MouseEvent<HTMLDivElement>) {
    const el = ref.current
    if (!el || !window.matchMedia('(hover: hover)').matches) return
    const rect = el.getBoundingClientRect()
    const px = (e.clientX - rect.left) / rect.width - 0.5
    const py = (e.clientY - rect.top) / rect.height - 0.5
    el.style.setProperty('--rx', `${(px * maxTilt * 2).toFixed(2)}deg`)
    el.style.setProperty('--ry', `${(-py * maxTilt * 2).toFixed(2)}deg`)
  }

  function handleMouseLeave() {
    const el = ref.current
    if (!el) return
    el.style.setProperty('--rx', '0deg')
    el.style.setProperty('--ry', '0deg')
  }

  return (
    <div
      ref={ref}
      className={`tilt-card ${className}`}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      {children}
    </div>
  )
}
