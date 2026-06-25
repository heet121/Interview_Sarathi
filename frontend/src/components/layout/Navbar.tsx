// src/components/layout/Navbar.tsx
import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { LogOut, User, BarChart2, Menu, X, Trophy, Terminal } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import toast from 'react-hot-toast'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate  = useNavigate()
  const location  = useLocation()
  const [drop,    setDrop]    = useState(false)
  const [mobile,  setMobile]  = useState(false)

  const isActive = (path: string) => location.pathname === path

  const handleLogout = () => {
    logout(); toast.success('Signed out'); navigate('/')
  }

  const initials = (user?.full_name || user?.email || '?')
    .split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)

  const links = [
    { to: '/', label: 'home' },
    { to: '/practice', label: 'practice' },
    ...(user ? [
      { to: '/dashboard', label: 'dashboard' },
      { to: '/leaderboard', label: 'leaderboard' },
    ] : []),
  ]

  return (
    <nav className="sticky top-0 z-50 bg-bg/95 backdrop-blur-md border-b-2 border-line">
      <div className="max-w-[1200px] mx-auto px-5 flex items-center justify-between gap-4"
        style={{ height: 64 }}>

        {/* Logo */}
        <Link to="/" className="flex items-center gap-2.5 shrink-0 no-underline group">
          <div className="w-9 h-9 bg-acid border-2 border-ink flex items-center justify-center
            text-ink shadow-[3px_3px_0_0_#0b0b0e] group-hover:shadow-[1px_1px_0_0_#0b0b0e]
            group-hover:translate-x-0.5 group-hover:translate-y-0.5 transition-all duration-100">
            <Terminal size={17} strokeWidth={2.6} />
          </div>
          <span className="font-mono text-[15px] font-bold tracking-tight text-paper">
            interview<span className="text-acid">_sarathi</span>
          </span>
        </Link>

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-1 flex-1 justify-center">
          {links.map(l => (
            <Link key={l.to} to={l.to}
              className={`px-3 py-1.5 font-mono text-[13px] no-underline border-2 transition-all duration-100
                ${isActive(l.to)
                  ? 'text-ink bg-acid border-ink'
                  : 'text-muted border-transparent hover:text-paper hover:border-line'}`}>
              <span className="text-muted2">{isActive(l.to) ? '> ' : '# '}</span>{l.label}
            </Link>
          ))}
        </div>

        {/* Right */}
        <div className="hidden md:flex items-center gap-2 shrink-0">
          {user ? (
            <div className="relative">
              <button onClick={() => setDrop(!drop)}
                className="flex items-center gap-2 pl-1.5 pr-3 py-1.5 border-2 border-line
                  bg-s1 hover:border-lineHi transition-all">
                <div className="w-6 h-6 bg-acid border-2 border-ink flex items-center justify-center
                  text-[10px] font-bold text-ink font-mono">
                  {initials}
                </div>
                <span className="text-paper max-w-[110px] truncate text-[13px] font-mono">
                  {user.full_name?.split(' ')[0] || user.email.split('@')[0]}
                </span>
              </button>

              {drop && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setDrop(false)} />
                  <div className="absolute right-0 top-full mt-2 w-56 bg-s1 border-2 border-line
                    shadow-[6px_6px_0_0_#0b0b0e] z-20 overflow-hidden">
                    <div className="px-4 py-3 border-b-2 border-line bg-[#15151b]">
                      <p className="text-[13px] font-bold text-paper truncate font-mono">{user.full_name || 'user'}</p>
                      <p className="text-[11px] text-muted2 truncate font-mono">{user.email}</p>
                    </div>
                    {[
                      { to: '/dashboard',    icon: BarChart2, label: 'dashboard' },
                      { to: '/leaderboard',  icon: Trophy,    label: 'leaderboard' },
                      { to: '/profile',      icon: User,      label: 'profile' },
                    ].map(item => (
                      <Link key={item.to} to={item.to} onClick={() => setDrop(false)}
                        className="flex items-center gap-2.5 px-4 py-2.5 text-[13px] font-mono text-muted
                          hover:text-ink hover:bg-acid transition-colors no-underline border-b border-line/60">
                        <item.icon size={14} />
                        {item.label}
                      </Link>
                    ))}
                    <button onClick={handleLogout}
                      className="w-full flex items-center gap-2.5 px-4 py-2.5 text-[13px] font-mono
                        text-bad hover:bg-bad hover:text-ink transition-colors">
                      <LogOut size={14} /> sign_out
                    </button>
                  </div>
                </>
              )}
            </div>
          ) : (
            <>
              <Link to="/login" className="btn-outline no-underline">Sign In</Link>
              <Link to="/practice" className="btn-primary no-underline">Start →</Link>
            </>
          )}
        </div>

        {/* Mobile toggle */}
        <button className="md:hidden text-paper border-2 border-line p-1.5 hover:border-acid transition-colors"
          onClick={() => setMobile(!mobile)}>
          {mobile ? <X size={18} /> : <Menu size={18} />}
        </button>
      </div>

      {/* Mobile menu */}
      {mobile && (
        <div className="md:hidden border-t-2 border-line bg-bg px-5 py-3 space-y-1">
          {links.map(l => (
            <Link key={l.to} to={l.to} onClick={() => setMobile(false)}
              className={`block px-3 py-2 font-mono text-sm no-underline border-2 transition-colors
                ${isActive(l.to) ? 'text-ink bg-acid border-ink' : 'text-muted border-transparent hover:border-line'}`}>
              <span className="text-muted2">{isActive(l.to) ? '> ' : '# '}</span>{l.label}
            </Link>
          ))}
          {user
            ? <button onClick={handleLogout}
                className="w-full text-left px-3 py-2 font-mono text-sm text-bad border-2 border-transparent">
                sign_out
              </button>
            : <Link to="/login" onClick={() => setMobile(false)}
                className="block btn-primary mt-2 text-center no-underline">
                Sign In
              </Link>
          }
        </div>
      )}
    </nav>
  )
}
