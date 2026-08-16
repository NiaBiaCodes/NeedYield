import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

export type UserRole = 'neighbor' | 'gardener' | 'organization'
export type AuthUser = { id: string; email: string; displayName: string; role: UserRole; demo: boolean; isAdmin?: boolean }
type StoredAuth = { user: AuthUser; accessToken?: string; refreshToken?: string }
type AuthContextValue = { user: AuthUser | null; loading: boolean; signUp: (input: { email: string; password: string; displayName: string; role: UserRole }) => Promise<string>; signIn: (email: string, password: string) => Promise<void>; continueAsDemo: (role: UserRole, isAdmin?: boolean) => void; signOut: () => Promise<void> }

const STORAGE_KEY = 'needyield-auth'
const SUPABASE_URL = (import.meta.env.VITE_SUPABASE_URL || '').replace(/\/$/, '')
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || ''
const AuthContext = createContext<AuthContextValue | null>(null)

function readStored(): StoredAuth | null { try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null') } catch { return null } }

async function supabaseAuth(path: string, body: Record<string, unknown>) {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) throw new Error('Supabase Auth is not configured yet. Use a demo account for now.')
  const response = await fetch(`${SUPABASE_URL}/auth/v1/${path}`, { method: 'POST', headers: { apikey: SUPABASE_ANON_KEY, 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(payload.msg || payload.error_description || payload.message || 'Authentication failed.')
  return payload
}

function userFromPayload(payload: any, fallback?: Partial<AuthUser>): AuthUser {
  const source = payload.user || payload; const metadata = source.user_metadata || {}
  const role: UserRole = ['neighbor', 'gardener', 'organization'].includes(metadata.role) ? metadata.role : fallback?.role || 'neighbor'
  return { id: source.id, email: source.email || fallback?.email || '', displayName: metadata.display_name || fallback?.displayName || source.email?.split('@')[0] || 'Neighbor', role, demo: false, isAdmin: false }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const initial = readStored(); const [user, setUser] = useState<AuthUser | null>(initial?.user || null); const [loading, setLoading] = useState(false)
  useEffect(() => {
    if (!initial?.refreshToken || initial.user.demo || !SUPABASE_URL) return
    supabaseAuth('token?grant_type=refresh_token', { refresh_token: initial.refreshToken }).then((payload) => { const next = { user: userFromPayload(payload, initial.user), accessToken: payload.access_token, refreshToken: payload.refresh_token }; localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); setUser(next.user) }).catch(() => { localStorage.removeItem(STORAGE_KEY); setUser(null) })
  }, [])
  const saveSession = (payload: any, fallback?: Partial<AuthUser>) => { const next = { user: userFromPayload(payload, fallback), accessToken: payload.access_token, refreshToken: payload.refresh_token }; localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); setUser(next.user) }
  const value = useMemo<AuthContextValue>(() => ({
    user, loading,
    signUp: async (input) => { setLoading(true); try { const payload = await supabaseAuth('signup', { email: input.email, password: input.password, data: { display_name: input.displayName, role: input.role } }); if (payload.access_token) { saveSession(payload, input); return 'Account created. Welcome to NeedYield!' } return 'Account created. Check your email to confirm it, then sign in.' } finally { setLoading(false) } },
    signIn: async (email, password) => { setLoading(true); try { saveSession(await supabaseAuth('token?grant_type=password', { email, password }), { email }) } finally { setLoading(false) } },
    continueAsDemo: (role, isAdmin = false) => { const demoUser: AuthUser = { id: isAdmin ? 'demo-admin' : `demo-${role}`, email: `${isAdmin ? 'admin' : role}@demo.needyield.local`, displayName: isAdmin ? 'Demo Admin' : role === 'gardener' ? 'Demo Gardener' : role === 'organization' ? 'Demo Organization' : 'Demo Neighbor', role, demo: true, isAdmin }; localStorage.setItem(STORAGE_KEY, JSON.stringify({ user: demoUser })); setUser(demoUser) },
    signOut: async () => { const stored = readStored(); if (stored?.accessToken && SUPABASE_URL && SUPABASE_ANON_KEY) await fetch(`${SUPABASE_URL}/auth/v1/logout`, { method: 'POST', headers: { apikey: SUPABASE_ANON_KEY, Authorization: `Bearer ${stored.accessToken}` } }).catch(() => undefined); localStorage.removeItem(STORAGE_KEY); setUser(null) },
  }), [user, loading])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() { const context = useContext(AuthContext); if (!context) throw new Error('useAuth must be used inside AuthProvider'); return context }
