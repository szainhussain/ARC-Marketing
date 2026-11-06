/** ARC mark: an original arc-over-baseline glyph (strategy → plan →
 * execution as one continuous stroke). Inline SVG, no external asset. */
export default function Logo({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id="arc-g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="var(--logo-from)" />
          <stop offset="1" stopColor="var(--logo-to)" />
        </linearGradient>
      </defs>
      <rect x="0.5" y="0.5" width="31" height="31" rx="8" fill="var(--color-surface)" stroke="var(--color-border-strong)" />
      <path d="M7 22 A9 9 0 0 1 25 22" fill="none" stroke="url(#arc-g)" strokeWidth="2.6" strokeLinecap="round" />
      <circle cx="25" cy="22" r="2.2" fill="var(--logo-dot)" />
      <path d="M7 25.5 H25" stroke="var(--color-border-strong)" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  )
}
