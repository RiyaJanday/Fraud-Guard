import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { fraudApi } from '../lib/api'

const AuthContext = createContext(null)

function initials(name) {
  if (!name) return 'FG'
  const parts = name.trim().split(/\s+/)
  return (parts[0][0] + (parts[1]?.[0] || '')).toUpperCase()
}

// UserOut (backend) -> the shape the rest of the UI (Topbar, Profile, etc.) expects
function mapUser(u) {
  return {
    id: u.id,
    name: u.full_name,
    email: u.email,
    role: u.role,
    org: 'FraudGuard', // backend has no org field yet — display-only placeholder
    avatar: initials(u.full_name),
    isVerified: u.is_verified,
  }
}

export function AuthProvider({ children }) {
  // Only a small, non-sensitive display cache (name/role/avatar initials) —
  // NEVER the access/refresh tokens themselves, which live exclusively in
  // httpOnly cookies the browser controls and this JS can't read. This
  // cache just avoids a name/avatar flash on reload; it is never trusted
  // as proof of an active session on its own (see the /auth/me check below).
  const [user, setUser] = useState(() => {
    const cached = localStorage.getItem('fraudguard_user')
    return cached ? JSON.parse(cached) : null
  })
  const [loading, setLoading] = useState(false)
  const [initializing, setInitializing] = useState(true)

  // On mount, always verify against the backend rather than trusting the
  // local cache — there's no client-readable token anymore to check for
  // presence/absence, so GET /auth/me (cookie-authenticated) is the only
  // real signal of whether a session is actually still valid.
  useEffect(() => {
    fraudApi
      .me()
      .then(({ data }) => {
        const nextUser = mapUser(data)
        localStorage.setItem('fraudguard_user', JSON.stringify(nextUser))
        setUser(nextUser)
      })
      .catch(() => {
        localStorage.removeItem('fraudguard_user')
        setUser(null)
      })
      .finally(() => setInitializing(false))
  }, [])

  const login = useCallback(async (email, password) => {
    setLoading(true)
    try {
      const { data } = await fraudApi.login({ email, password })
      // No token handling here — /auth/login's Set-Cookie headers already
      // put the httpOnly auth cookies + csrf_token cookie in place.
      const nextUser = mapUser(data.user)
      localStorage.setItem('fraudguard_user', JSON.stringify(nextUser))
      setUser(nextUser)
      return nextUser
    } finally {
      setLoading(false)
    }
  }, [])

  const register = useCallback(async ({ full_name, email, password, role }) => {
    setLoading(true)
    try {
      await fraudApi.register({ full_name, email, password, role: role || 'analyst' })
      // Backend register doesn't establish a session itself, so log in right after.
      const { data } = await fraudApi.login({ email, password })
      const nextUser = mapUser(data.user)
      localStorage.setItem('fraudguard_user', JSON.stringify(nextUser))
      setUser(nextUser)
      return nextUser
    } finally {
      setLoading(false)
    }
  }, [])

  const logout = useCallback(() => {
    fraudApi.logout().catch(() => {}) // best-effort server-side revoke + cookie clear
    localStorage.removeItem('fraudguard_user')
    setUser(null)
  }, [])

  // Merges partial fields (e.g. after a profile save) into the cached user
  // so Topbar/Profile reflect the change immediately without a full re-fetch.
  const updateUser = useCallback((partial) => {
    setUser((prev) => {
      const next = { ...prev, ...partial }
      localStorage.setItem('fraudguard_user', JSON.stringify(next))
      return next
    })
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, initializing, login, register, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
