import { Link, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useWorkspace } from '../context/WorkspaceContext'

export default function AppLayout() {
  const { user, memberships, logout } = useAuth()
  const { activeOrganizationId, setActiveOrganizationId } = useWorkspace()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/sign-in')
  }

  return (
    <div>
      <nav className="app-nav">
        <span className="brand">Marketing Department Harness</span>
        <Link to="/app">Overview</Link>
        <Link to="/app/campaigns">Campaigns</Link>
        <Link to="/app/brand">Brand profile</Link>
        <Link to="/app/reports">Reports</Link>
        <Link to="/app/integrations">Integrations</Link>
        <span className="spacer" />
        {memberships.length > 1 && (
          <select
            value={activeOrganizationId || ''}
            onChange={(e) => setActiveOrganizationId(e.target.value)}
          >
            {memberships.map((m) => (
              <option key={m.organization_id} value={m.organization_id}>
                {m.organization_name}
              </option>
            ))}
          </select>
        )}
        <span className="muted">{user?.full_name}</span>
        <button className="secondary" onClick={handleLogout}>
          Sign out
        </button>
      </nav>
      <Outlet />
    </div>
  )
}
