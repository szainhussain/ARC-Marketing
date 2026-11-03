import { motion, useReducedMotion } from 'motion/react'
import type { ReactNode } from 'react'

/**
 * Scroll-triggered fade+rise reveal, following the ui-ux-pro-max skill's
 * "Standard Scroll Reveal" guidance: 12-24px y-offset, ~400-500ms,
 * power2-like easing, triggers once near viewport entry. Automatically
 * renders the final state with no animation when the user has
 * prefers-reduced-motion set (useReducedMotion), rather than a manual
 * media-query guard per component.
 */
export default function Reveal({
  children,
  delay = 0,
  y = 16,
  className,
}: {
  children: ReactNode
  delay?: number
  y?: number
  className?: string
}) {
  const reduceMotion = useReducedMotion()

  if (reduceMotion) {
    return <div className={className}>{children}</div>
  }

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.5, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  )
}
