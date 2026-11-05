// Which list in each deliverable holds the posts / variants / ads that can get
// generated images, and how to name one. Mirrors ITEM_LISTS in app/services/media_service.py.
export const IMAGE_ITEMS: Record<string, { key: string; label: (x: Record<string, unknown>, i: number) => string }> = {
  content_pack: { key: 'variants', label: (x, i) => String(x.headline || `Variant ${i + 1}`) },
  social_calendar: { key: 'calendar_entries', label: (x, i) => [x.day, x.channel].filter(Boolean).join(' · ') || `Post ${i + 1}` },
  paid_media_plan: { key: 'campaign_structure', label: (x, i) => String(x.name || `Ad campaign ${i + 1}`) },
}

export function supportsImages(type: string) {
  return type in IMAGE_ITEMS
}
