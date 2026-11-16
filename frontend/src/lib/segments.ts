// The business types ARC is built for first (UAE SMEs), with the answers most
// of them would give. Used to pre-fill onboarding, the Growth Audit form and
// campaign playbooks so nobody starts from a blank box. Everything stays editable.

export type Segment = {
  key: string
  label: string
  industry: string
  businessType: 'b2c' | 'b2b' | 'both'
  channels: string[]
  goals: string[]
  playbook: { name: string; objective: string; offer: string; channels: string; success_metrics: string }
}

export const SEGMENTS: Segment[] = [
  {
    key: 'home_services',
    label: 'Home services & maintenance',
    industry: 'Home services and maintenance',
    businessType: 'b2c',
    channels: ['Google Ads', 'Google Business Profile', 'WhatsApp', 'Instagram'],
    goals: ['More booked jobs', 'More repeat and contract customers', 'More reviews'],
    playbook: {
      name: 'Booked jobs: [month]',
      objective: 'Get [number] booked jobs this month from people searching for [service] in [areas].',
      offer: 'Fixed-price [service] with same-day or next-day slots',
      channels: 'Google Ads, Google Business Profile, WhatsApp, Instagram',
      success_metrics: 'Booked jobs, cost per booked job, calls and WhatsApp enquiries, new reviews',
    },
  },
  {
    key: 'beauty',
    label: 'Salon, spa & beauty',
    industry: 'Salons, spas and beauty',
    businessType: 'b2c',
    channels: ['Instagram', 'TikTok', 'WhatsApp', 'Google Business Profile'],
    goals: ['Fill quiet days', 'More repeat bookings', 'Launch a new treatment'],
    playbook: {
      name: 'Fill weekday bookings: [month]',
      objective: 'Fill [number] weekday appointments this month and bring back clients who have not visited in [weeks] weeks.',
      offer: 'Weekday package or add-on for [treatment]',
      channels: 'Instagram, TikTok, WhatsApp, Google Business Profile',
      success_metrics: 'Bookings, returning clients, cost per booking, reviews',
    },
  },
  {
    key: 'retail_ecommerce',
    label: 'Specialist retail & e-commerce',
    industry: 'Specialist retail and e-commerce',
    businessType: 'b2c',
    channels: ['Instagram', 'Meta ads', 'Google Ads', 'Email', 'Website'],
    goals: ['More online orders', 'Higher order value', 'More repeat purchases'],
    playbook: {
      name: 'Online sales: [month or season]',
      objective: 'Reach [amount] in online sales this month while staying above break-even return on ad spend.',
      offer: '[Bundle or seasonal offer] until [end date]',
      channels: 'Instagram, Meta ads, Google Ads, email, website',
      success_metrics: 'Orders, revenue, return on ad spend, average order value, repeat orders',
    },
  },
  {
    key: 'education',
    label: 'Education & training',
    industry: 'Education and training',
    businessType: 'both',
    channels: ['Instagram', 'LinkedIn', 'Google Ads', 'Email', 'Website'],
    goals: ['More enrolments', 'More enquiries for a new course', 'Fill an upcoming intake'],
    playbook: {
      name: 'Enrolments: [intake]',
      objective: 'Get [number] enrolments for [course] before the [date] intake.',
      offer: 'Early enrolment price or free trial class',
      channels: 'Instagram, LinkedIn, Google Ads, email, website',
      success_metrics: 'Enquiries, enrolments, cost per enrolment, trial-class attendance',
    },
  },
  {
    key: 'professional_services',
    label: 'Professional services',
    industry: 'Professional services',
    businessType: 'b2b',
    channels: ['LinkedIn', 'Email', 'Website', 'Google Ads'],
    goals: ['More qualified enquiries', 'More consultations booked', 'Win larger clients'],
    playbook: {
      name: 'Qualified enquiries: [quarter]',
      objective: 'Generate [number] qualified enquiries from [type of client] this quarter.',
      offer: 'Free consultation or short assessment',
      channels: 'LinkedIn, email, website, Google Ads',
      success_metrics: 'Qualified enquiries, consultations booked, cost per enquiry, proposals sent',
    },
  },
]

export const OTHER_SEGMENT = 'other'

export const BUDGET_BANDS = ['Under $500 / month', '$500 to $1,500 / month', '$1,500 to $5,000 / month', '$5,000 to $15,000 / month', 'Over $15,000 / month', 'Not decided yet']

export const UAE_REGIONS = ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'Ras Al Khaimah', 'Fujairah', 'Umm Al Quwain', 'All UAE', 'GCC']

export const ALL_CHANNELS = ['Instagram', 'Facebook', 'TikTok', 'LinkedIn', 'WhatsApp', 'Google Ads', 'Meta ads', 'Google Business Profile', 'Email', 'Website', 'Blog', 'Events']

export const TONES = ['Friendly and warm', 'Professional and precise', 'Premium and calm', 'Playful and bold', 'Expert and reassuring']
