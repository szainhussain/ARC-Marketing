/** Recharts styling from theme tokens, so charts follow light/dark and the chosen accent.
 * SVG presentation attributes and inline styles both resolve var() at render time. */
export const CHART = {
  grid: 'var(--chart-grid)',
  accent: 'var(--color-accent)',
  accent2: 'var(--color-accent-2)',
  success: 'var(--color-success)',
  danger: 'var(--color-danger)',
  warning: 'var(--color-warning)',
  successFill: 'color-mix(in srgb, var(--color-success) 15%, transparent)',
  dangerFill: 'color-mix(in srgb, var(--color-danger) 10%, transparent)',
}

export const TOOLTIP = {
  contentStyle: {
    background: 'var(--chart-tooltip-bg)',
    border: '1px solid var(--chart-tooltip-border)',
    borderRadius: 8,
    fontSize: 12,
    color: 'var(--color-fg)',
  },
  labelStyle: { color: 'var(--color-fg)' },
  itemStyle: { color: 'var(--color-fg)' },
  cursor: { fill: 'var(--chart-cursor)' },
}

export const AXIS = { stroke: 'var(--chart-axis)', tick: { fill: 'var(--chart-axis)' }, fontSize: 11, tickLine: false, axisLine: false }

/** Axis label for a cost: up to 3 decimals under $1 ("$0.015", "$0.004"), cents above,
 * so small-cost ticks stay distinct instead of rounding to "$0.01" / "$0.00". */
export function costTick(v: number): string {
  if (v === 0) return '$0'
  return v < 1 ? `$${Number(v.toFixed(3))}` : `$${v.toFixed(2)}`
}
