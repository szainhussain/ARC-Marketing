// Content for the sales pages: solutions, the operating loop, FAQs and the
// marketing scorecard. Kept as data so copy changes don't touch layout code.
import type { Faq } from './seo'

export const LOOP = [
  { k: 'Strategy', d: 'ARC sets objectives, positioning, KPIs and a budget split for the month.' },
  { k: 'Plan', d: 'The strategy becomes a dated plan for each channel you use.' },
  { k: 'Create', d: 'Posts, ads, emails, web pages and sales materials are drafted in parallel, in your brand voice.' },
  { k: 'You approve', d: 'Nothing leaves ARC until an approver signs off on the exact version.', highlight: true },
  { k: 'Publish', d: 'Approved work is exported in each platform’s format or sent to Zapier or Make.' },
  { k: 'Measure', d: 'Record results per channel and see cost per lead, ROAS and what worked.' },
  { k: 'Improve', d: 'Learnings you approve feed the next month’s strategy and plan.' },
] as const

// What a customer actually receives from a run. Each line maps to a real
// deliverable type; keep it in step with app/agents/definitions.py.
export const MONTHLY_OUTCOMES = [
  { title: 'A clear plan for the month', body: 'Objectives, KPIs, a budget split and a dated plan for each channel you use.' },
  { title: 'Posts ready to publish', body: 'A posting calendar with captions and timing, written in your brand voice.' },
  { title: 'Ads ready to launch', body: 'Campaign structure and ad copy checked against Google, Meta and TikTok field limits, with a budget recommendation you approve.' },
  { title: 'Pages that get found', body: 'Search themes for your market, page improvements and a blog article you can publish to WordPress.' },
  { title: 'Emails and replies drafted', body: 'Outreach emails, answers to common customer objections and reply templates for reviews and messages.' },
  { title: 'A report that shows profit', body: 'Record results per channel and see whether each one made or lost money at your margins, not just clicks and return on ad spend.' },
] as const

export type Solution = {
  slug: string
  title: string
  short: string
  who: string
  pains: string[]
  delivers: { agent: string; output: string }[]
  outcome: string
}

export const SOLUTIONS: Solution[] = [
  {
    slug: 'product-launch',
    title: 'Launch a product or offer',
    short: 'A coordinated launch plan, content and channel mix, ready to approve in one run.',
    who: 'Founders and marketing leads launching a product, service, feature or seasonal offer.',
    pains: [
      'Launch plans live in scattered docs and chat threads',
      'Messaging changes from one channel to the next',
      'Content is late because everything waits on one person',
    ],
    delivers: [
      { agent: 'Chief Marketing Officer', output: 'Launch objectives, positioning and KPIs' },
      { agent: 'Research Analyst', output: 'Audience, competitor and trend notes, facts separated from inference' },
      { agent: 'Marketing Manager', output: 'Phased launch plan with owners and dates' },
      { agent: 'Creative Studio', output: 'Core copy and channel variants' },
      { agent: 'Social Media Manager', output: 'Launch-week posting calendar' },
      { agent: 'Performance Marketing', output: 'Paid campaign structure and budget recommendation' },
    ],
    outcome: 'One brief in, a reviewed launch package out, with every piece version-locked for approval.',
  },
  {
    slug: 'local-business',
    title: 'Grow a local business',
    short: 'Always-on local marketing without hiring an agency or a full-time marketer.',
    who: 'Clinics, studios, restaurants, trades, schools and other service businesses.',
    pains: [
      'No time to plan marketing between serving customers',
      'Agency retainers are too expensive for the results',
      'Posting is inconsistent, so nothing builds momentum',
    ],
    delivers: [
      { agent: 'Chief Marketing Officer', output: 'A simple monthly strategy tied to bookings or enquiries' },
      { agent: 'Social Media Manager', output: 'A month of posts with captions and timing' },
      { agent: 'SEO & Growth', output: 'Local keyword themes and page improvements' },
      { agent: 'Customer Insights', output: 'Likely objections and reply templates for reviews and messages' },
      { agent: 'Record Keeper', output: 'What was decided, what to do next, and what to remember' },
    ],
    outcome: 'A marketing rhythm that runs every month, with you approving in minutes instead of writing for hours.',
  },
  {
    slug: 'ecommerce',
    title: 'Sell more online',
    short: 'Campaigns, product content and paid structure for online stores.',
    who: 'E-commerce brands and online sellers running promotions and product drops.',
    pains: [
      'Every promotion starts from a blank page',
      'Product pages and ads are written in a hurry',
      'Spend decisions are made without a plan',
    ],
    delivers: [
      { agent: 'Research Analyst', output: 'Customer segments and competitor offers' },
      { agent: 'SEO & Growth', output: 'Product-page and metadata drafts, conversion ideas' },
      { agent: 'Creative Studio', output: 'Promotion copy and creative briefs' },
      { agent: 'Performance Marketing', output: 'Campaign structure and budget split: ARC never spends by itself' },
      { agent: 'Marketing Ops', output: 'A quality check for brand rules and unsupported claims' },
    ],
    outcome: 'Promotions planned end to end, exported in each ad platform’s format, ready to launch.',
  },
  {
    slug: 'b2b-leads',
    title: 'Generate B2B leads',
    short: 'Positioning, content and sales enablement that work together.',
    who: 'B2B companies and consultancies that sell through a sales team or partners.',
    pains: [
      'Marketing and sales tell different stories',
      'Thought leadership is planned but never published',
      'Partner and account marketing is an afterthought',
    ],
    delivers: [
      { agent: 'Chief Marketing Officer', output: 'Positioning and pipeline-focused KPIs' },
      { agent: 'Creative Studio', output: 'Thought-leadership and campaign content' },
      { agent: 'Key Accounts & Sales Enablement', output: 'Account segments and enablement materials' },
      { agent: 'PR & Partnerships', output: 'Target outlets, partners and outreach drafts' },
      { agent: 'Customer Insights', output: 'Objection handling for the sales team' },
    ],
    outcome: 'Marketing and sales working from the same plan, with every outreach draft reviewed before it goes out.',
  },
]

export const HOME_FAQS: Faq[] = [
  {
    q: 'How is ARC different from ChatGPT or an AI writing tool?',
    a: 'Writing tools answer one prompt at a time. ARC does the whole job in order: it sets a strategy, turns it into a dated plan, writes the content for each channel, checks it against your brand rules, and tracks results. Nothing leaves the workspace until a person approves the exact version.',
  },
  {
    q: 'Will ARC post or spend money without asking?',
    a: 'No. Every outbound action needs an explicit approval tied to one exact version. Agents cannot change ad spend, make payments or sign anything. Those are locked platform rules.',
  },
  {
    q: 'Can ARC publish to my channels?',
    a: 'Today ARC exports approved work in Meta, Google Ads and TikTok formats and can send approved content to Zapier or Make, which connect to thousands of apps. Native publishing connectors are being added one channel at a time.',
  },
  {
    q: 'Is my data used to train AI?',
    a: 'No. Your content is only sent to the AI provider to generate your drafts, under terms that do not allow training on it. You can export or delete your workspace at any time.',
  },
  {
    q: 'How long does it take to get started?',
    a: 'Create an account, fill in your business profile and write a short brief. Your first campaign run starts immediately, and the 14-day trial needs no card.',
  },
  {
    q: 'Do I still need a marketer?',
    a: 'ARC does the planning, drafting and coordination. Someone on your side still decides what to approve. If you want human help too, we offer a strategist add-on.',
  },
]

export const PRICING_FAQS: Faq[] = [
  { q: 'Is there a free trial?', a: 'Yes. Every new workspace starts with a 14-day trial of the Launch plan. No card is needed.' },
  { q: 'Can I cancel any time?', a: 'Yes. Cancel from the Billing page and your plan stays active until the end of the period you paid for.' },
  { q: 'What counts as a campaign run?', a: 'One run takes one campaign brief from strategy to finished, checked work: the plan, the content for the channels you chose, a quality review and a record of what was decided.' },
  { q: 'What happens if I reach a limit?', a: 'The backend stops new runs once a monthly limit is reached and tells you why. Nothing is charged automatically; you can upgrade or wait for the next month.' },
  { q: 'Are prices final?', a: 'Prices are provisional while ARC is in early access. Any change is announced at least 30 days ahead and applies from your next billing period.' },
  { q: 'Do you offer human help?', a: 'Yes, a strategist add-on for monthly planning calls and quarterly reviews. Book a demo to discuss it.' },
]

export type ScoreQuestion = { id: string; q: string; options: { label: string; points: number }[]; area: string; tip: string }

export const SCORECARD: ScoreQuestion[] = [
  { id: 'strategy', area: 'Strategy', q: 'Do you have a written marketing strategy with goals for this quarter?', tip: 'Start every quarter with written objectives, positioning and 2–3 KPIs.',
    options: [{ label: 'Yes, and we review it', points: 3 }, { label: 'Roughly, not written down', points: 1 }, { label: 'No', points: 0 }] },
  { id: 'audience', area: 'Audience', q: 'How well do you know who you are marketing to?', tip: 'Document your top two customer segments, their problems and where they spend time.',
    options: [{ label: 'Documented segments and needs', points: 3 }, { label: 'A general idea', points: 1 }, { label: 'Not sure', points: 0 }] },
  { id: 'plan', area: 'Planning', q: 'Do you plan campaigns at least a month ahead?', tip: 'Keep a rolling 30-day plan with owners and dates for every campaign.',
    options: [{ label: 'Yes, with a calendar', points: 3 }, { label: 'Sometimes', points: 1 }, { label: 'We react week to week', points: 0 }] },
  { id: 'consistency', area: 'Consistency', q: 'How consistently do you publish content?', tip: 'Pick a sustainable rhythm per channel and stick to it before adding channels.',
    options: [{ label: 'Every week, on schedule', points: 3 }, { label: 'A few times a month', points: 2 }, { label: 'Rarely', points: 0 }] },
  { id: 'brand', area: 'Brand', q: 'Is your brand voice written down (tone, words to use and avoid)?', tip: 'Write a one-page brand voice guide so every channel sounds like one company.',
    options: [{ label: 'Yes', points: 3 }, { label: 'Partly', points: 1 }, { label: 'No', points: 0 }] },
  { id: 'review', area: 'Quality', q: 'Does someone review content before it goes out?', tip: 'Use a simple approval step so nothing ships with wrong claims or off-brand copy.',
    options: [{ label: 'Always', points: 3 }, { label: 'Sometimes', points: 1 }, { label: 'Never', points: 0 }] },
  { id: 'measure', area: 'Measurement', q: 'Do you track results per channel (leads, sales, cost)?', tip: 'Track at least spend, leads and cost per lead for each channel every month.',
    options: [{ label: 'Yes, monthly', points: 3 }, { label: 'Only some channels', points: 1 }, { label: 'No', points: 0 }] },
  { id: 'learn', area: 'Learning', q: 'Do you change your plan based on what worked last month?', tip: 'End each month with three learnings and one change to next month’s plan.',
    options: [{ label: 'Yes, every month', points: 3 }, { label: 'Occasionally', points: 1 }, { label: 'No', points: 0 }] },
]
