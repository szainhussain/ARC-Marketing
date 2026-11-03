import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { useAuth } from './AuthContext'

type WorkspaceState = {
  activeOrganizationId: string | null
  setActiveOrganizationId: (id: string | null) => void
}

const WorkspaceContext = createContext<WorkspaceState | null>(null)

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const { memberships } = useAuth()
  const [activeOrganizationId, setActiveOrganizationIdState] = useState<string | null>(
    () => localStorage.getItem('activeOrganizationId'),
  )

  useEffect(() => {
    if (!activeOrganizationId && memberships.length > 0) {
      setActiveOrganizationIdState(memberships[0].organization_id)
    }
  }, [memberships, activeOrganizationId])

  function setActiveOrganizationId(id: string | null) {
    setActiveOrganizationIdState(id)
    if (id) localStorage.setItem('activeOrganizationId', id)
    else localStorage.removeItem('activeOrganizationId')
  }

  return (
    <WorkspaceContext.Provider value={{ activeOrganizationId, setActiveOrganizationId }}>
      {children}
    </WorkspaceContext.Provider>
  )
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext)
  if (!ctx) throw new Error('useWorkspace must be used within WorkspaceProvider')
  return ctx
}
