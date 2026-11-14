// One place for the facts every legal page depends on. Change the company
// name here once an entity is registered; bump TERMS_VERSION (and
// TERMS_VERSION in app/config.py) whenever the Terms or Privacy Policy change.

export const LEGAL = {
  company: 'ARC',
  product: 'ARC',
  site: 'https://usearc.vercel.app',
  effectiveDate: '5 November 2026',
  version: '2026-11-05',
  contactPath: '/contact',
  // Days of notice before a material change to the Terms or a new sub-processor.
  noticeDays: 30,
  deletionGraceDays: 30,
} as const

export const TERMS_VERSION = LEGAL.version

export const LEGAL_DOCS = [
  { to: '/terms', title: 'Terms of Service', blurb: 'The agreement for using ARC: accounts, plans, your content, AI output and liability.' },
  { to: '/privacy', title: 'Privacy Policy', blurb: 'What personal data we collect, why, who processes it and your rights where you live.' },
  { to: '/dpa', title: 'Data Processing Agreement', blurb: 'How we process your workspace data on your behalf, for customers who need a DPA.' },
  { to: '/ai-policy', title: 'AI Use Policy', blurb: 'How the agents work, what they can never do, and how your data is (not) used for training.' },
  { to: '/acceptable-use', title: 'Acceptable Use Policy', blurb: 'What ARC must not be used for.' },
  { to: '/cookies', title: 'Cookie Policy', blurb: 'The only cookie we use, and the preferences stored in your browser.' },
  { to: '/subprocessors', title: 'Sub-processors', blurb: 'Every company that processes data for ARC, what for, and where.' },
  { to: '/refunds', title: 'Refunds and Cancellation', blurb: 'Trials, cancelling, pausing and when refunds apply.' },
]

export type Subprocessor = {
  name: string
  purpose: string
  data: string
  location: string
  status: 'active' | 'when_enabled'
  link: string
}

export const SUBPROCESSORS: Subprocessor[] = [
  { name: 'Vercel Inc.', purpose: 'Website hosting and content delivery', data: 'Requests to the website, IP address', location: 'United States (global edge network)', status: 'active', link: 'https://vercel.com/legal/privacy-policy' },
  { name: 'Render Services, Inc.', purpose: 'Application servers that run the ARC API and agents', data: 'All workspace data in transit and in processing', location: 'United States (Virginia)', status: 'active', link: 'https://render.com/privacy' },
  { name: 'Supabase, Inc.', purpose: 'Database and file storage', data: 'All stored workspace data and uploaded files', location: 'United States (AWS us-east-1)', status: 'active', link: 'https://supabase.com/privacy' },
  { name: 'Groq, Inc.', purpose: 'AI model inference for agent drafts', data: 'Campaign briefs, business profile and approved knowledge sent in prompts', location: 'United States', status: 'active', link: 'https://groq.com/privacy-policy/' },
  { name: 'Anthropic, PBC', purpose: 'AI model inference for agent drafts (alternative provider)', data: 'Campaign briefs, business profile and approved knowledge sent in prompts', location: 'United States', status: 'when_enabled', link: 'https://www.anthropic.com/legal/privacy' },
  { name: 'Google LLC (Gemini API)', purpose: 'On-brand image generation and semantic search for Ask ARC', data: 'Brand Kit, post and ad copy, knowledge and deliverable text sent for images and search', location: 'United States and other Google regions', status: 'when_enabled', link: 'https://ai.google.dev/gemini-api/terms' },
  { name: 'Stripe, Inc.', purpose: 'Subscription payments and invoicing', data: 'Billing contact, payment details (held by Stripe, never by ARC)', location: 'United States and other Stripe regions', status: 'when_enabled', link: 'https://stripe.com/privacy' },
  { name: 'Resend, Inc.', purpose: 'Transactional email (sign-in, invitations, notifications)', data: 'Name, email address, email content', location: 'United States', status: 'when_enabled', link: 'https://resend.com/legal/privacy-policy' },
]

export type RegionId = 'eu' | 'uk' | 'us' | 'ca' | 'au' | 'ae' | 'pk' | 'in' | 'row'

export type Region = {
  id: RegionId
  label: string
  law: string
  rights: string[]
  complaint: string
  transfers: string
  consumer: string
}

export const REGIONS: Region[] = [
  {
    id: 'eu',
    label: 'European Union, EEA and Switzerland',
    law: 'the EU General Data Protection Regulation (GDPR) and, in Switzerland, the Federal Act on Data Protection (FADP)',
    rights: [
      'Access a copy of your personal data',
      'Correct inaccurate or incomplete data',
      'Erase your data ("right to be forgotten")',
      'Restrict processing while a concern is resolved',
      'Receive your data in a portable format',
      'Object to processing based on our legitimate interests, and to direct marketing at any time',
      'Withdraw consent at any time, where we rely on consent',
    ],
    complaint: 'You can lodge a complaint with the data protection supervisory authority in the country where you live or work.',
    transfers:
      'When your data is processed outside the EEA or Switzerland (mainly in the United States), we rely on an adequacy decision where one applies, or on the European Commission’s Standard Contractual Clauses with our providers.',
    consumer:
      'If you use ARC as a consumer rather than for your business, you keep every right that the mandatory consumer law of your country gives you, including the right to bring a claim in the courts where you live.',
  },
  {
    id: 'uk',
    label: 'United Kingdom',
    law: 'the UK GDPR and the Data Protection Act 2018',
    rights: [
      'Access a copy of your personal data',
      'Correct inaccurate or incomplete data',
      'Erase your data',
      'Restrict processing',
      'Receive your data in a portable format',
      'Object to processing based on legitimate interests, and to direct marketing at any time',
      'Withdraw consent at any time, where we rely on consent',
    ],
    complaint: 'You can complain to the Information Commissioner’s Office (ico.org.uk).',
    transfers:
      'When your data is processed outside the UK, we rely on UK adequacy regulations where they apply, or on the UK International Data Transfer Agreement or the UK Addendum to the EU Standard Contractual Clauses.',
    consumer:
      'If you are a consumer, nothing in these Terms affects your statutory rights, including under the Consumer Rights Act 2015, and you may bring a claim in the courts of the part of the UK where you live.',
  },
  {
    id: 'us',
    label: 'United States',
    law: 'applicable U.S. state privacy laws, including the California Consumer Privacy Act as amended by the California Privacy Rights Act (CCPA)',
    rights: [
      'Know the categories and specific pieces of personal information we collect, use and disclose',
      'Delete personal information we hold about you',
      'Correct inaccurate personal information',
      'Opt out of the sale or sharing of personal information: ARC does not sell personal information or share it for cross-context behavioural advertising',
      'Limit the use of sensitive personal information: ARC does not use it to infer characteristics about you',
      'Not be discriminated against for exercising these rights',
      'Use an authorised agent to make a request on your behalf',
    ],
    complaint:
      'If we decline a request, you can appeal by replying to our decision. You can also contact your state Attorney General and, in California, the California Privacy Protection Agency.',
    transfers: 'ARC’s infrastructure is located in the United States.',
    consumer: 'Nothing in these Terms limits rights you have under the consumer protection laws of your state.',
  },
  {
    id: 'ca',
    label: 'Canada',
    law: 'the Personal Information Protection and Electronic Documents Act (PIPEDA) and applicable provincial laws, including Québec’s Law 25',
    rights: [
      'Access the personal information we hold about you',
      'Correct inaccurate information',
      'Withdraw consent, subject to legal or contractual limits',
      'Ask how your information has been used and to whom it was disclosed',
    ],
    complaint:
      'You can complain to the Office of the Privacy Commissioner of Canada, or to your provincial privacy commissioner where provincial law applies.',
    transfers:
      'Your information is processed in the United States by our service providers and may be accessible to authorities there under U.S. law.',
    consumer: 'Nothing in these Terms limits rights you have under the consumer protection laws of your province.',
  },
  {
    id: 'au',
    label: 'Australia',
    law: 'the Privacy Act 1988 (Cth) and the Australian Privacy Principles',
    rights: ['Access the personal information we hold about you', 'Correct inaccurate, out-of-date or incomplete information'],
    complaint:
      'Please contact us first; if you are not satisfied with our response, you can complain to the Office of the Australian Information Commissioner (OAIC).',
    transfers: 'Your information is processed in the United States by the providers listed on our sub-processor page.',
    consumer:
      'Our services come with guarantees that cannot be excluded under the Australian Consumer Law. Nothing in these Terms excludes, restricts or modifies those guarantees.',
  },
  {
    id: 'ae',
    label: 'United Arab Emirates',
    law: 'Federal Decree-Law No. 45 of 2021 on the Protection of Personal Data (PDPL) and, if you are in the DIFC or ADGM, their data protection laws',
    rights: [
      'Obtain information about, and a copy of, your personal data',
      'Correct inaccurate data',
      'Erase data that is no longer needed or was processed unlawfully',
      'Restrict or stop processing in the cases the law allows',
      'Object to processing, including for direct marketing',
      'Receive your data in a structured, machine-readable format',
    ],
    complaint:
      'You can complain to the UAE Data Office or, in the DIFC or ADGM, to the DIFC Commissioner of Data Protection or the ADGM Office of Data Protection.',
    transfers:
      'Your data is processed outside the UAE (mainly in the United States) under contractual safeguards with our providers, as permitted by applicable law.',
    consumer: 'Nothing in these Terms limits rights you have under UAE consumer protection law.',
  },
  {
    id: 'pk',
    label: 'Pakistan',
    law: 'applicable Pakistani law, including the Prevention of Electronic Crimes Act, 2016, and any personal data protection law in force',
    rights: [
      'Access the personal data we hold about you',
      'Correct inaccurate data',
      'Delete your data or export it',
      'Object to marketing communications',
    ],
    complaint: 'Please contact us first. You may also approach the authority responsible for data protection under the law in force.',
    transfers: 'Your data is processed outside Pakistan (mainly in the United States) by the providers on our sub-processor page.',
    consumer: 'Nothing in these Terms limits rights you have under the consumer protection laws of your province.',
  },
  {
    id: 'in',
    label: 'India',
    law: 'the Digital Personal Data Protection Act, 2023 and the rules made under it',
    rights: [
      'Obtain a summary of the personal data we process and the processing activities',
      'Correct, complete, update or erase your personal data',
      'Withdraw consent at any time, as easily as you gave it',
      'Have your grievance addressed by us',
      'Nominate a person to exercise your rights in case of death or incapacity',
    ],
    complaint:
      'Raise your grievance with us through the contact form first. If it is not resolved, you can approach the Data Protection Board of India.',
    transfers: 'Your data is processed outside India (mainly in the United States) as permitted by applicable law.',
    consumer: 'Nothing in these Terms limits rights you have under the Consumer Protection Act, 2019.',
  },
  {
    id: 'row',
    label: 'All other countries',
    law: 'the data protection and privacy laws that apply to you',
    rights: [
      'Access the personal data we hold about you',
      'Correct inaccurate data',
      'Delete your data or export it',
      'Object to marketing communications and withdraw consent',
    ],
    complaint: 'Please contact us first. You may also have the right to complain to your local data protection authority.',
    transfers: 'Your data is processed in the United States by the providers on our sub-processor page.',
    consumer: 'Nothing in these Terms limits mandatory rights you have under the consumer protection laws of your country.',
  },
]

const EEA_TZ = new Set(
  'Amsterdam Andorra Athens Berlin Bratislava Brussels Bucharest Budapest Busingen Copenhagen Dublin Helsinki Lisbon Ljubljana Luxembourg Madrid Malta Mariehamn Monaco Oslo Paris Prague Riga Rome San_Marino Sofia Stockholm Tallinn Vaduz Vatican Vienna Vilnius Warsaw Zagreb Zurich Nicosia'
    .split(' ')
    .map((c) => `Europe/${c}`)
    .concat(['Atlantic/Reykjavik', 'Atlantic/Canary', 'Atlantic/Madeira', 'Atlantic/Azores', 'Asia/Nicosia', 'Asia/Famagusta']),
)
const UK_TZ = new Set(['Europe/London', 'Europe/Belfast', 'Europe/Guernsey', 'Europe/Jersey', 'Europe/Isle_of_Man'])
const CA_CITIES = new Set(
  'Toronto Vancouver Montreal Edmonton Winnipeg Halifax St_Johns Regina Moncton Glace_Bay Goose_Bay Whitehorse Yellowknife Iqaluit Dawson_Creek Fort_Nelson Creston Rankin_Inlet Resolute Cambridge_Bay Inuvik Atikokan Swift_Current Dawson Blanc-Sablon Nipigon Thunder_Bay Rainy_River Pangnirtung'.split(' '),
)
const US_TZ_PREFIX = ['America/Indiana/', 'America/Kentucky/', 'America/North_Dakota/', 'US/']
const US_TZ = new Set(
  'New_York Chicago Denver Los_Angeles Phoenix Anchorage Detroit Boise Juneau Adak Nome Sitka Yakutat Metlakatla Menominee Puerto_Rico'
    .split(' ')
    .map((c) => `America/${c}`)
    .concat(['Pacific/Honolulu']),
)
const EU_CC = new Set('AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE IS LI NO CH'.split(' '))
const CC_REGION: Record<string, RegionId> = { GB: 'uk', US: 'us', CA: 'ca', AU: 'au', AE: 'ae', PK: 'pk', IN: 'in' }

/** Best guess of the visitor's region from their time zone, then browser language. */
export function detectRegion(timeZone?: string, languages?: readonly string[]): RegionId {
  const tz = timeZone ?? safeTimeZone()
  if (tz) {
    if (UK_TZ.has(tz)) return 'uk'
    if (EEA_TZ.has(tz)) return 'eu'
    if (US_TZ.has(tz) || US_TZ_PREFIX.some((p) => tz.startsWith(p))) return 'us'
    if (tz.startsWith('America/') && CA_CITIES.has(tz.slice('America/'.length))) return 'ca'
    if (tz.startsWith('Canada/')) return 'ca'
    if (tz.startsWith('Australia/')) return 'au'
    if (tz === 'Asia/Dubai') return 'ae'
    if (tz === 'Asia/Karachi') return 'pk'
    if (tz === 'Asia/Kolkata' || tz === 'Asia/Calcutta') return 'in'
  }
  const langs = languages ?? (typeof navigator !== 'undefined' ? navigator.languages || [navigator.language] : [])
  for (const lang of langs) {
    const cc = (lang || '').split('-')[1]?.toUpperCase()
    if (!cc) continue
    if (CC_REGION[cc]) return CC_REGION[cc]
    if (EU_CC.has(cc)) return 'eu'
  }
  return 'row'
}

function safeTimeZone(): string | undefined {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone
  } catch {
    return undefined
  }
}

const REGION_KEY = 'arc-legal-region'

export function loadRegion(): RegionId {
  try {
    const saved = localStorage.getItem(REGION_KEY) as RegionId | null
    if (saved && REGIONS.some((r) => r.id === saved)) return saved
  } catch {
    /* storage blocked: fall back to detection */
  }
  return detectRegion()
}

export function saveRegion(id: RegionId) {
  try {
    localStorage.setItem(REGION_KEY, id)
  } catch {
    /* storage blocked: choice lasts for this page view only */
  }
}

export function regionById(id: RegionId): Region {
  return REGIONS.find((r) => r.id === id) || REGIONS[REGIONS.length - 1]
}
