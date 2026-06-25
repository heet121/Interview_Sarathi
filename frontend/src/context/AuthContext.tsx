// src/context/AuthContext.tsx
import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { authApi, UserOut } from '@/lib/api'

interface Ctx {
  user: UserOut | null
  token: string | null
  loading: boolean
  login:   (token: string, user: UserOut) => void
  logout:  () => void
  refresh: () => Promise<void>
}

const AuthContext = createContext<Ctx>({} as Ctx)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user,    setUser]    = useState<UserOut | null>(null)
  const [token,   setToken]   = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const t = localStorage.getItem('token')
    const u = localStorage.getItem('user')
    if (t && u) {
      try { setToken(t); setUser(JSON.parse(u)) } catch { /* corrupted */ }
    }
    setLoading(false)
  }, [])

  const login = (newToken: string, newUser: UserOut) => {
    localStorage.setItem('token', newToken)
    localStorage.setItem('user', JSON.stringify(newUser))
    setToken(newToken); setUser(newUser)
  }

  const logout = () => {
    localStorage.removeItem('token'); localStorage.removeItem('user')
    setToken(null); setUser(null)
  }

  const refresh = async () => {
    try {
      const res = await authApi.me()
      setUser(res.data)
      localStorage.setItem('user', JSON.stringify(res.data))
    } catch { logout() }
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
