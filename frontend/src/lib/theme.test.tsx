import { describe, expect, it } from 'vitest'
import { ACCENT_IDS, ACCENTS, SURFACES, brandTone, contrast, resolveTone, type Theme } from './theme'

const THEMES: Theme[] = ['dark', 'light']

describe('accent presets meet WCAG AA', () => {
  for (const id of ACCENT_IDS) {
    for (const theme of THEMES) {
      it(`${id} / ${theme}`, () => {
        const t = ACCENTS[id][theme]
        const s = SURFACES[theme]
        for (const bg of [s.bg, s.surface, s.surface2]) {
          expect(contrast(t.accent, bg)).toBeGreaterThanOrEqual(4.5) // links and accent text
          expect(contrast(t.accent2, bg)).toBeGreaterThanOrEqual(4.5)
          expect(contrast(t.hover, bg)).toBeGreaterThanOrEqual(4.5)
        }
        expect(contrast(t.onAccent, t.accent)).toBeGreaterThanOrEqual(4.5) // text on accent buttons/chips
      })
    }
  }
})

describe('brand colours are made readable', () => {
  // Pale yellow is unreadable on white; dark navy is unreadable on near-black.
  for (const brand of ['#FFD700', '#0A2540', '#635BFF', '#00FF00', '#FFFFFF', '#000000']) {
    for (const theme of THEMES) {
      it(`${brand} in ${theme}`, () => {
        const t = brandTone(brand, theme)
        const s = SURFACES[theme]
        for (const bg of [s.bg, s.surface, s.surface2]) expect(contrast(t.accent, bg)).toBeGreaterThanOrEqual(4.5)
        expect(contrast(t.onAccent, t.accent)).toBeGreaterThanOrEqual(4.5)
      })
    }
  }
  it('keeps an already-readable brand colour unchanged', () => {
    expect(brandTone('#4338ca', 'light').accent).toBe('#4338ca')
  })
})

describe('which accent applies', () => {
  const brandWs = { accent: 'brand' as const, brandHex: '#0A2540' }
  it('a personal preset beats the workspace', () => {
    expect(resolveTone('light', 'rose', brandWs)).toEqual(ACCENTS.rose.light)
  })
  it('"workspace" follows the workspace preset or brand colour', () => {
    expect(resolveTone('dark', 'workspace', { accent: 'emerald', brandHex: null })).toEqual(ACCENTS.emerald.dark)
    expect(resolveTone('light', 'workspace', brandWs).accent).toBe('#0a2540')
  })
  it('falls back to ARC Blue with no workspace, or brand chosen but no colour', () => {
    expect(resolveTone('dark', 'workspace', null)).toEqual(ACCENTS.arc.dark)
    expect(resolveTone('light', 'workspace', { accent: 'brand', brandHex: null })).toEqual(ACCENTS.arc.light)
  })
})
