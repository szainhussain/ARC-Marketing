import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import ProtectedRoute from './components/ProtectedRoute'
import CampaignListPage from './pages/CampaignListPage'
import CampaignWorkspacePage from './pages/CampaignWorkspacePage'
import CreateWorkspacePage from './pages/CreateWorkspacePage'
import DashboardPage from './pages/DashboardPage'
import IntegrationsPage from './pages/IntegrationsPage'
import LandingPage from './pages/LandingPage'
import NewCampaignPage from './pages/NewCampaignPage'
import OnboardingPage from './pages/OnboardingPage'
import ReportsPage from './pages/ReportsPage'
import SignInPage from './pages/SignInPage'
import SignUpPage from './pages/SignUpPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/sign-in" element={<SignInPage />} />
      <Route path="/sign-up" element={<SignUpPage />} />
      <Route
        path="/create-workspace"
        element={
          <ProtectedRoute>
            <CreateWorkspacePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/app"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="onboarding" element={<OnboardingPage />} />
        <Route path="brand" element={<OnboardingPage />} />
        <Route path="campaigns" element={<CampaignListPage />} />
        <Route path="campaigns/new" element={<NewCampaignPage />} />
        <Route path="campaigns/:campaignId" element={<CampaignWorkspacePage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="integrations" element={<IntegrationsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
