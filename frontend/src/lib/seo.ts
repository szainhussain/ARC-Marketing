import { useEffect } from 'react'

const SITE = 'ARC'
const DEFAULT_DESCRIPTION =
  'ARC plans your month, writes every post, ad and email, and shows which channels brought customers and which lost money. Nothing goes out until you approve it. Built for growing businesses in the UAE.'

function setMeta(name: string, content: string, attr: 'name' | 'property' = 'name') {
  let el = document.head.querySelector<HTMLMetaElement>(`meta[${attr}="${name}"]`)
  if (!el) {
    el = document.createElement('meta')
    el.setAttribute(attr, name)
    document.head.appendChild(el)
  }
  el.setAttribute('content', content)
}

/** Sets the tab title, meta description and Open Graph tags for a public page. */
export function usePageMeta(title: string, description: string = DEFAULT_DESCRIPTION) {
  useEffect(() => {
    const full = title ? `${title} · ${SITE}` : `${SITE}: Strategy. Plan. Execution.`
    document.title = full
    setMeta('description', description)
    setMeta('og:title', full, 'property')
    setMeta('og:description', description, 'property')
    setMeta('og:type', 'website', 'property')
    setMeta('og:url', window.location.origin + window.location.pathname, 'property')
    setMeta('twitter:title', full)
    setMeta('twitter:description', description)
  }, [title, description])
}

/** Adds a JSON-LD block (e.g. FAQPage) for search engines while the page is mounted. */
export function useJsonLd(id: string, data: unknown) {
  const json = JSON.stringify(data)
  useEffect(() => {
    const el = document.createElement('script')
    el.type = 'application/ld+json'
    el.id = `ld-${id}`
    el.text = json
    document.head.appendChild(el)
    return () => el.remove()
  }, [id, json])
}

export type Faq = { q: string; a: string }

export function faqJsonLd(faqs: Faq[]) {
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: faqs.map((f) => ({ '@type': 'Question', name: f.q, acceptedAnswer: { '@type': 'Answer', text: f.a } })),
  }
}
