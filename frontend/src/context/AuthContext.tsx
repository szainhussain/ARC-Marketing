import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { apiRequest, clearCsrfTokenCache } from '../api/client'
import type { Membership, User } from '../api/types'

type AuthState = {
  user: User | null
  memberships: Membership[]
  loading: boolean
  refresh: () => Promise<void>
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName: string, acceptTerms: boolean) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [memberships, setMemberships] = useState<Membership[]>([])
  const [loading, setLoading] = useState(true)

  async function refresh() {
    try {
      const data = await apiRequest<{ user: User; memberships: Membership[] }>('/me')
      setUser(data.user)
      setMemberships(data.memberships)
    } catch {
      setUser(null)
      setMemberships([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // refresh() is intentionally called only once, on mount
    refresh()
  }, [])

  async function login(email: string, password: string) {
    const data = await apiRequest<{ user: User }>('/auth/login', {
      method: 'POST',
      body: { email, password },
    })
    setUser(data.user)
    await refresh()
  }

  async function register(email: string, password: string, fullName: string, acceptTerms: boolean) {
    const data = await apiRequest<{ user: User }>('/auth/register', {
      method: 'POST',
      body: { email, password, full_name: fullName, accept_terms: acceptTerms },
    })
    setUser(data.user)
    await refresh()
  }

  async function logout() {
    await apiRequest('/auth/logout', { method: 'POST' })
    clearCsrfTokenCache()
    setUser(null)
    setMemberships([])
  }

  return (
    <AuthContext.Provider value={{ user, memberships, loading, refresh, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
