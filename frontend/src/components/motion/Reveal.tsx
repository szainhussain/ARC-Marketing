import { motion, useReducedMotion } from 'motion/react'
import type { ReactNode } from 'react'

/**
 * Scroll-triggered rise from an already-visible default: content is never
 * hidden (it stays readable if the observer never fires, in screenshots,
 * print and slow devices); only a short ease-out rise plays once near
 * viewport entry. Automatically
 * renders the final state with no animation when the user has
 * prefers-reduced-motion set (useReducedMotion), rather than a manual
 * media-query guard per component.
 */
export default function Reveal({
  children,
  delay = 0,
  y = 10,
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
      initial={{ opacity: 1, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.5, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  )
}
