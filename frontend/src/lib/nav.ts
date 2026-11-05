import {
  Activity,
  BadgeDollarSign,
  BarChart3,
  Bell,
  BookOpen,
  Bot,
  CalendarDays,
  CheckSquare,
  CreditCard,
  FileText,
  Gauge,
  Image,
  Inbox,
  LayoutDashboard,
  Mail,
  ListChecks,
  Megaphone,
  TrendingUp,
  Palette,
  Plug,
  Rocket,
  ScrollText,
  Search,
  Settings,
  Shield,
  SlidersHorizontal,
  Users,
  type LucideIcon,
} from 'lucide-react'

export type NavItem = { to: string; label: string; icon: LucideIcon; keywords?: string }

export const NAV_GROUPS: { label: string; items: NavItem[] }[] = [
  {
    label: 'Command',
    items: [
      { to: '/app/dashboard', label: 'Command Center', icon: LayoutDashboard, keywords: 'overview kpi home' },
      { to: '/app/operations', label: 'Operations', icon: Gauge, keywords: 'agents queue control room' },
      { to: '/app/approvals', label: 'Approvals', icon: CheckSquare, keywords: 'inbox decisions' },
      { to: '/app/results', label: 'Results', icon: TrendingUp, keywords: 'leads spend roas revenue monthly report performance' },
      { to: '/app/notifications', label: 'Notifications', icon: Bell },
    ],
  },
  {
    label: 'Work',
    items: [
      { to: '/app/campaigns', label: 'Campaigns', icon: Megaphone, keywords: 'briefs runs' },
      { to: '/app/tasks', label: 'Tasks', icon: ListChecks, keywords: 'queue retry' },
      { to: '/app/agents', label: 'Agents', icon: Bot, keywords: 'team twelve' },
      { to: '/app/calendar', label: 'Calendar', icon: CalendarDays, keywords: 'schedule posts' },
      { to: '/app/outreach', label: 'Outreach', icon: Mail, keywords: 'email contacts lists unsubscribe brevo resend' },
      { to: '/app/ads', label: 'Ads', icon: BadgeDollarSign, keywords: 'launch spend budget cap meta google kill switch' },
      { to: '/app/content', label: 'Content', icon: FileText, keywords: 'deliverables drafts' },
      { to: '/app/research', label: 'Research', icon: Search, keywords: 'insights audience' },
    ],
  },
  {
    label: 'Brand & data',
    items: [
      { to: '/app/brand', label: 'Brand profile', icon: Palette, keywords: 'business profile tone' },
      { to: '/app/knowledge', label: 'Knowledge', icon: BookOpen, keywords: 'library learnings faq' },
      { to: '/app/assets', label: 'Assets', icon: Image, keywords: 'uploads files logo' },
      { to: '/app/analytics', label: 'Analytics', icon: BarChart3, keywords: 'reports metrics export' },
      { to: '/app/integrations', label: 'Integrations', icon: Plug, keywords: 'connectors meta google tiktok' },
    ],
  },
  {
    label: 'Workspace',
    items: [
      { to: '/app/team', label: 'Team', icon: Users, keywords: 'members invite roles' },
      { to: '/app/billing', label: 'Billing', icon: CreditCard, keywords: 'plan subscription' },
      { to: '/app/settings', label: 'Settings', icon: Settings },
      { to: '/app/settings/automation', label: 'Automation', icon: SlidersHorizontal, keywords: 'policies budgets concurrency' },
      { to: '/app/settings/usage', label: 'Usage', icon: Activity, keywords: 'cost tokens limits' },
      { to: '/app/settings/security', label: 'Security', icon: Shield, keywords: 'password sessions export delete' },
      { to: '/app/audit-log', label: 'Audit log', icon: ScrollText, keywords: 'history events' },
      { to: '/app/onboarding', label: 'Onboarding', icon: Rocket, keywords: 'setup wizard' },
    ],
  },
]

// Shown only to platform admins (PLATFORM_ADMIN_EMAILS on the server).
export const ADMIN_GROUP = {
  label: 'Platform',
  items: [{ to: '/app/admin', label: 'Admin inbox', icon: Inbox, keywords: 'demo requests leads enquiries signups' }],
}

export const ALL_NAV: NavItem[] = NAV_GROUPS.flatMap((g) => g.items)
