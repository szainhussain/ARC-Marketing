import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes, useParams } from 'react-router-dom'
import { PageSkeleton } from './components/ui'
import AppLayout from './components/AppLayout'
import ProtectedRoute from './components/ProtectedRoute'
import PublicLayout from './components/PublicLayout'
const AgentDetailPage = lazy(() => import('./pages/AgentDetailPage'))
const ApprovalsPage = lazy(() => import('./pages/ApprovalsPage'))
const CampaignWorkspacePage = lazy(() => import('./pages/CampaignWorkspacePage'))
import CreateWorkspacePage from './pages/CreateWorkspacePage'
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const NewCampaignPage = lazy(() => import('./pages/NewCampaignPage'))
const OnboardingPage = lazy(() => import('./pages/OnboardingPage'))
const BrandPage = lazy(() => import('./pages/OnboardingPage').then((m) => ({ default: m.BrandPage })))
const OperationsPage = lazy(() => import('./pages/OperationsPage'))
const TasksPage = lazy(() => import('./pages/TasksPage'))
const AnalyticsPage = lazy(() => import('./pages/app/DataPages').then((m) => ({ default: m.AnalyticsPage })))
const AssetsPage = lazy(() => import('./pages/app/DataPages').then((m) => ({ default: m.AssetsPage })))
const IntegrationsPage = lazy(() => import('./pages/app/DataPages').then((m) => ({ default: m.IntegrationsPage })))
const KnowledgePage = lazy(() => import('./pages/app/DataPages').then((m) => ({ default: m.KnowledgePage })))
const AgentsDirectoryPage = lazy(() => import('./pages/app/WorkPages').then((m) => ({ default: m.AgentsDirectoryPage })))
const CalendarPage = lazy(() => import('./pages/app/WorkPages').then((m) => ({ default: m.CalendarPage })))
const CampaignListPage = lazy(() => import('./pages/app/WorkPages').then((m) => ({ default: m.CampaignListPage })))
const ContentPage = lazy(() => import('./pages/app/WorkPages').then((m) => ({ default: m.ContentPage })))
const ResearchPage = lazy(() => import('./pages/app/WorkPages').then((m) => ({ default: m.ResearchPage })))
const AuditLogPage = lazy(() => import('./pages/app/WorkspacePages').then((m) => ({ default: m.AuditLogPage })))
const AutomationSettingsPage = lazy(() => import('./pages/app/WorkspacePages').then((m) => ({ default: m.AutomationSettingsPage })))
const BillingPage = lazy(() => import('./pages/app/WorkspacePages').then((m) => ({ default: m.BillingPage })))
const NotificationsPage = lazy(() => import('./pages/app/WorkspacePages').then((m) => ({ default: m.NotificationsPage })))
const SecuritySettingsPage = lazy(() => import('./pages/app/WorkspacePages').then((m) => ({ default: m.SecuritySettingsPage })))
const SettingsPage = lazy(() => import('./pages/app/WorkspacePages').then((m) => ({ default: m.SettingsPage })))
const TeamPage = lazy(() => import('./pages/app/WorkspacePages').then((m) => ({ default: m.TeamPage })))
const TestCheckoutPage = lazy(() => import('./pages/app/WorkspacePages').then((m) => ({ default: m.TestCheckoutPage })))
const ReviewPage = lazy(() => import('./pages/public/ReviewPage'))
const AdminPage = lazy(() => import('./pages/app/AdminPage'))
const UsagePage = lazy(() => import('./pages/app/WorkspacePages').then((m) => ({ default: m.UsagePage })))
import {
  AcceptInvitePage,
  ForgotPasswordPage,
  LoginPage,
  ResetPasswordPage,
  SignupPage,
  VerifyEmailPage,
} from './pages/public/AuthPages'
import HomePage from './pages/public/HomePage'
import { AgencyComparePage, DemoPage, ScorecardPage, SolutionPage, SolutionsPage } from './pages/public/GrowthPages'
import {
  AboutPage,
  AgentsPage,
  ContactPage,
  DocsPage,
  HowItWorksPage,
  IntegrationsPublicPage,
  PricingPage,
  ProductPage,
  SecurityPage,
} from './pages/public/InfoPages'
const AcceptableUsePage = lazy(() => import('./pages/public/LegalPages').then((m) => ({ default: m.AcceptableUsePage })))
const AiPolicyPage = lazy(() => import('./pages/public/LegalPages').then((m) => ({ default: m.AiPolicyPage })))
const CookiesPage = lazy(() => import('./pages/public/LegalPages').then((m) => ({ default: m.CookiesPage })))
const DpaPage = lazy(() => import('./pages/public/LegalPages').then((m) => ({ default: m.DpaPage })))
const LegalHubPage = lazy(() => import('./pages/public/LegalPages').then((m) => ({ default: m.LegalHubPage })))
const PrivacyPage = lazy(() => import('./pages/public/LegalPages').then((m) => ({ default: m.PrivacyPage })))
const RefundsPage = lazy(() => import('./pages/public/LegalPages').then((m) => ({ default: m.RefundsPage })))
const SubprocessorsPage = lazy(() => import('./pages/public/LegalPages').then((m) => ({ default: m.SubprocessorsPage })))
const TermsPage = lazy(() => import('./pages/public/LegalPages').then((m) => ({ default: m.TermsPage })))

function AgentAlias() {
  const { agentId } = useParams()
  return <Navigate to={`/app/agents/${agentId}`} replace />
}

export default function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/product" element={<ProductPage />} />
        <Route path="/solutions" element={<SolutionsPage />} />
        <Route path="/solutions/:slug" element={<SolutionPage />} />
        <Route path="/demo" element={<DemoPage />} />
        <Route path="/review/:token" element={<ReviewPage />} />
        <Route path="/marketing-scorecard" element={<ScorecardPage />} />
        <Route path="/compare/agency" element={<AgencyComparePage />} />
        <Route path="/agents" element={<AgentsPage />} />
        <Route path="/how-it-works" element={<HowItWorksPage />} />
        <Route path="/integrations" element={<IntegrationsPublicPage />} />
        <Route path="/security" element={<SecurityPage />} />
        <Route path="/pricing" element={<PricingPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/contact" element={<ContactPage />} />
        <Route path="/docs" element={<DocsPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="/legal" element={<LegalHubPage />} />
        <Route path="/cookies" element={<CookiesPage />} />
        <Route path="/dpa" element={<DpaPage />} />
        <Route path="/acceptable-use" element={<AcceptableUsePage />} />
        <Route path="/ai-policy" element={<AiPolicyPage />} />
        <Route path="/subprocessors" element={<SubprocessorsPage />} />
        <Route path="/refunds" element={<RefundsPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/accept-invite" element={<AcceptInvitePage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route
          path="/create-workspace"
          element={
            <ProtectedRoute>
              <CreateWorkspacePage />
            </ProtectedRoute>
          }
        />
      </Route>
      <Route path="/sign-in" element={<Navigate to="/login" replace />} />
      <Route path="/sign-up" element={<Navigate to="/signup" replace />} />
      <Route
        path="/app"
        element={
          <ProtectedRoute>
            <Suspense fallback={<PageSkeleton />}>
              <AppLayout />
            </Suspense>
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="onboarding" element={<OnboardingPage />} />
        <Route path="brand" element={<BrandPage />} />
        <Route path="campaigns" element={<CampaignListPage />} />
        <Route path="campaigns/new" element={<NewCampaignPage />} />
        <Route path="campaigns/:campaignId" element={<CampaignWorkspacePage section="overview" />} />
        <Route path="campaigns/:campaignId/workflow" element={<CampaignWorkspacePage section="workflow" />} />
        <Route path="campaigns/:campaignId/deliverables" element={<CampaignWorkspacePage section="deliverables" />} />
        <Route path="agents" element={<AgentsDirectoryPage />} />
        <Route path="agents/:agentId" element={<AgentDetailPage />} />
        <Route path="operations" element={<OperationsPage />} />
        <Route path="operations/agents/:agentId" element={<AgentDetailPage />} />
        <Route path="tasks" element={<TasksPage />} />
        <Route path="approvals" element={<ApprovalsPage />} />
        <Route path="calendar" element={<CalendarPage />} />
        <Route path="content" element={<ContentPage />} />
        <Route path="assets" element={<AssetsPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="reports" element={<Navigate to="/app/analytics" replace />} />
        <Route path="research" element={<ResearchPage />} />
        <Route path="integrations" element={<IntegrationsPage />} />
        <Route path="knowledge" element={<KnowledgePage />} />
        <Route path="team" element={<TeamPage />} />
        <Route path="billing" element={<BillingPage />} />
        <Route path="billing/test-checkout" element={<TestCheckoutPage />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="settings/security" element={<SecuritySettingsPage />} />
        <Route path="settings/automation" element={<AutomationSettingsPage />} />
        <Route path="settings/usage" element={<UsagePage />} />
        <Route path="audit-log" element={<AuditLogPage />} />
        <Route path="admin" element={<AdminPage />} />
        <Route path="ops/agents/:agentId" element={<AgentAlias />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
