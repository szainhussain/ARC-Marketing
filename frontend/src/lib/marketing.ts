import { BookOpenCheck, Gauge, Globe, Headphones, Layers, LineChart, PenTool, ShieldCheck, Target, Workflow } from 'lucide-react'

export const CAPABILITIES = [
  { icon: Workflow, title: 'Autonomous campaign orchestration', body: 'A durable task graph: each agent starts when its inputs are ready, retries on its own, and stops cleanly when it can’t proceed.' },
  { icon: PenTool, title: 'Brand-aware content creation', body: 'Every draft uses your tone and is checked in code for your prohibited phrases before a person sees it.' },
  { icon: Layers, title: 'Multi-channel execution', body: 'Social calendars, paid structures, SEO drafts and outreach, exported in each platform’s format for your team to publish.' },
  { icon: Target, title: 'Paid media oversight', body: 'Structures, experiments and budget splits as recommendations. No agent can change spend, ever.' },
  { icon: Headphones, title: 'Customer insight analysis', body: 'Themes, objections and response templates, with sensitive situations always routed to a person.' },
  { icon: Globe, title: 'SEO and e-commerce growth', body: 'Keyword themes by intent, metadata drafts and conversion experiments, no live site changes without you.' },
  { icon: LineChart, title: 'Performance intelligence', body: 'Observed platform metrics kept separate from estimates; business metrics shown as unavailable until a real source is connected.' },
  { icon: ShieldCheck, title: 'Human approvals and governance', body: 'Approvals are tied to the exact version you reviewed. Change one word and the approval is invalidated.' },
  { icon: BookOpenCheck, title: 'Continuous learning', body: 'The Record Keeper proposes learnings after each run; once you approve them, every future run uses them.' },
  { icon: Gauge, title: 'Integration and workflow management', body: 'One control room for agents, queue, costs and controls, including a one-click stop for everything.' },
]

export const INTEGRATION_STATUS_LABEL: Record<string, string> = {
  available_tested: 'Available & tested',
  architecture_supported: 'Supported in architecture, not built',
  planned: 'Planned',
}
