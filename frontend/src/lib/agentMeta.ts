import {
  Brain,
  Briefcase,
  ClipboardList,
  Globe,
  Handshake,
  Headphones,
  LineChart,
  Microscope,
  Archive,
  MessageCircle,
  PenTool,
  Target,
  type LucideIcon,
} from 'lucide-react'

/** Presentation-only extras for each agent. Responsibilities, outputs,
 * dependencies, tools and integration status come from the live registry
 * (GET /public/agents) so the site can't drift from what's built. */
export const AGENT_META: Record<string, { icon: LucideIcon; short: string; example: string }> = {
  cmo: { icon: Brain, short: 'CMO', example: 'Turns “grow trial sign-ups 25% this quarter” into objectives, positioning and KPIs.' },
  marketing_manager: { icon: ClipboardList, short: 'Marketing Manager', example: 'Builds a phased 6-week plan and routes work to the right specialists.' },
  social_media: { icon: MessageCircle, short: 'Social', example: 'Turns approved copy into a dated Instagram and TikTok calendar with escalation rules.' },
  pr_partnerships: { icon: Handshake, short: 'PR & Partnerships', example: 'Defines creator and media profiles to target and drafts outreach for you to approve.' },
  paid_media: { icon: Target, short: 'Paid Media', example: 'Proposes campaign structure and a budget split, you decide the spend.' },
  creative_studio: { icon: PenTool, short: 'Creative', example: 'Writes the creative brief and channel-ready copy variants in your brand voice.' },
  research_analyst: { icon: Microscope, short: 'Research', example: 'Separates what your profile states from what it infers about audience and competitors.' },
  customer_insights: { icon: Headphones, short: 'Customer Insights', example: 'Drafts response templates and flags which ones must go to a person.' },
  seo_growth: { icon: Globe, short: 'SEO & Growth', example: 'Plans keyword themes by intent and drafts page titles and meta descriptions.' },
  key_accounts: { icon: Briefcase, short: 'Key Accounts', example: 'Identifies account segments and the enablement materials sales needs.' },
  marketing_ops: { icon: LineChart, short: 'Ops & Governance', example: 'Quality-gates every draft and reports unsupported claims before anything is approved.' },
  record_keeper: { icon: Archive, short: 'Record Keeper', example: 'Records decisions and action items, and proposes learnings for the knowledge library.' },
}

export type AgentTeam = { key: string; name: string; responsibility: string }

export type PublicAgent = {
  team?: AgentTeam
  agent_id: string
  number: number
  name: string
  version: string
  role: string
  responsibilities: string[]
  task_type: string
  depends_on: string[]
  reads: string[]
  outputs: string[]
  kpis: string[]
  escalates: string[]
  allowed_tools: string[]
  allowed_integrations: { name: string; status: string }[]
  approval_policy: { external_actions: string }
  evaluation_checks: string[]
}

/** 30-second explainer video per agent, served from public/videos/agents/.
 * Source project and re-render steps: ARC_Demo_Video/Agent_Explainers (outside the repo). */
const AGENTS_WITH_VIDEO = new Set(Object.keys(AGENT_META))
export function agentVideo(agentId: string): { src: string; poster: string; captions: string } | null {
  if (!AGENTS_WITH_VIDEO.has(agentId)) return null
  const base = `/videos/agents/${agentId}`
  return { src: `${base}.mp4`, poster: `${base}.jpg`, captions: `${base}.vtt` }
}
