// src/pages/LoginPage.tsx
import { useState, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Eye, EyeOff, Mail, Lock, ArrowRight, X, Terminal } from 'lucide-react'
import toast from 'react-hot-toast'
import { authApi, errMsg } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import { Spinner } from '@/components/ui'

type Tab = 'login' | 'register'

export default function LoginPage() {
  const { login, user } = useAuth()
  const navigate        = useNavigate()
  const [params]        = useSearchParams()
  const [tab, setTab]   = useState<Tab>('login')
  const [showPw, setShowPw]   = useState(false)
  const [loading, setLoading] = useState(false)

  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')

  const [reg, setReg] = useState({
    email:'', password:'', full_name:'',
    college:'', branch:'', graduation_year:'', cgpa:'',
  })

  useEffect(() => { if (user) navigate('/dashboard', { replace: true }) }, [user])

  useEffect(() => {
    const err = params.get('error')
    if (err === 'google_failed')  toast.error('Google sign-in failed. Try again.')
    if (err === 'github_failed')  toast.error('GitHub sign-in failed. Make sure your email is public.')
  }, [params])

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || !password) return toast.error('Fill in all fields')
    setLoading(true)
    try {
      const res = await authApi.login({ email, password })
      login(res.data.access_token, res.data.user)
      toast.success(`Welcome back, ${res.data.user.full_name?.split(' ')[0] || 'there'}`)
      navigate('/dashboard')
    } catch (e) { toast.error(errMsg(e)) }
    finally { setLoading(false) }
  }

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!reg.email || !reg.password || !reg.full_name)
      return toast.error('Name, email and password are required')
    if (reg.password.length < 8)
      return toast.error('Password must be at least 8 characters')
    setLoading(true)
    try {
      const res = await authApi.register(reg)
      login(res.data.access_token, res.data.user)
      toast.success('Account created — welcome to Interview Sarathi')
      navigate('/dashboard')
    } catch (e) { toast.error(errMsg(e)) }
    finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen bg-bg flex">

      {/* Left — compiler panel */}
      <div className="hidden lg:flex flex-col w-[440px] shrink-0 border-r-2 border-line bg-s1 p-8">
        <Link to="/" className="flex items-center gap-2.5 no-underline mb-10">
          <div className="w-9 h-9 bg-acid border-2 border-ink flex items-center justify-center text-ink shadow-[3px_3px_0_0_#0b0b0e]">
            <Terminal size={17} strokeWidth={2.6} />
          </div>
          <span className="font-mono text-[15px] font-bold text-paper">
            interview<span className="text-acid">_sarathi</span>
          </span>
        </Link>

        <div className="term flex-1 flex flex-col shadow-brutal">
          <div className="term-bar">
            <span className="term-dot bg-bad" />
            <span className="term-dot bg-warn" />
            <span className="term-dot bg-ok" />
            <span className="ml-2">auth — session.ts</span>
          </div>
          <div className="p-5 font-mono text-[13px] leading-relaxed space-y-1.5 flex-1">
            <p><span className="text-muted2">{'// '}</span><span className="text-cyan">import</span> {'{ mockInterview }'} <span className="text-cyan">from</span> <span className="text-acid">'@sarathi/core'</span></p>
            <p className="text-muted2">{'// Practice as a Software Engineer.'}</p>
            <p><span className="text-violet">const</span> session = <span className="text-cyan">await</span> mockInterview({'{'}</p>
            <p className="pl-4">voice: <span className="text-acid">true</span>,</p>
            <p className="pl-4">judge: <span className="text-acid">'deberta-v3'</span>,</p>
            <p className="pl-4">posture: <span className="text-acid">true</span>,</p>
            <p>{'}'})</p>
            <p className="pt-3 text-muted">Real-time voice · DeBERTa scoring · posture analysis</p>
            <p className="text-muted2">Built for Indian placement drives.</p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2 mt-6">
          {[['10K+','Students'],['94%','Satisfaction'],['50+','Companies']].map(([v,l]) => (
            <div key={l} className="card p-3 text-center">
              <div className="font-mono text-lg font-bold text-acid">{v}</div>
              <div className="text-[10px] text-muted2 uppercase tracking-wider">{l}</div>
            </div>
          ))}
        </div>

        <p className="text-[11px] font-mono text-muted2 mt-6">© 2025 interview_sarathi</p>
      </div>

      {/* Right — auth form */}
      <div className="flex-1 flex flex-col items-center justify-center p-6 relative grid-bg">
        <button onClick={() => navigate('/')}
          className="absolute top-5 right-5 btn-outline text-[11px] py-1.5">
          <X size={12} /> skip
        </button>

        <div className="flex lg:hidden items-center gap-2 mb-8">
          <div className="w-8 h-8 bg-acid border-2 border-ink flex items-center justify-center">
            <Terminal size={14} className="text-ink" />
          </div>
          <span className="font-mono text-sm font-bold text-paper">interview<span className="text-acid">_sarathi</span></span>
        </div>

        <div className="w-full max-w-[400px] fade-up">
          <p className="nb-eyebrow mb-2">// auth</p>
          <h1 className="text-2xl text-paper mb-6">{tab === 'login' ? 'Sign in' : 'Create account'}</h1>

          <div className="flex border-2 border-line mb-6">
            {(['login','register'] as Tab[]).map(t => (
              <button key={t} onClick={() => setTab(t)}
                className={`flex-1 py-2.5 font-mono text-sm font-bold uppercase tracking-wide transition-colors
                  ${tab === t ? 'bg-acid text-ink' : 'bg-s1 text-muted hover:text-paper'}`}>
                {t === 'login' ? 'sign_in' : 'register'}
              </button>
            ))}
          </div>

          <div className="space-y-2.5 mb-5">
            <button onClick={() => { window.location.href = authApi.googleUrl() }}
              className="w-full flex items-center justify-center gap-3 py-3 px-4 border-2 border-line bg-s1
                text-sm font-mono text-paper hover:border-acid transition-colors">
              <svg width="18" height="18" viewBox="0 0 18 18"><path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z" fill="#4285F4"/><path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z" fill="#34A853"/><path d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/><path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/></svg>
              google_oauth()
            </button>
            <button onClick={() => { window.location.href = authApi.githubUrl() }}
              className="w-full flex items-center justify-center gap-3 py-3 px-4 border-2 border-line bg-s1
                text-sm font-mono text-paper hover:border-acid transition-colors">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/></svg>
              github_oauth()
            </button>
          </div>

          <div className="flex items-center gap-3 mb-5">
            <div className="flex-1 h-0.5 bg-line" />
            <span className="text-[11px] font-mono text-muted2">or email</span>
            <div className="flex-1 h-0.5 bg-line" />
          </div>

          {tab === 'login' && (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="label">Email</label>
                <div className="relative">
                  <Mail size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted2" />
                  <input type="email" className="input pl-9" placeholder="you@college.edu"
                    value={email} onChange={e => setEmail(e.target.value)} required />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="label !mb-0">Password</label>
                  <Link to="/forgot-password" className="text-[11px] font-mono text-acid hover:underline no-underline">
                    forgot?
                  </Link>
                </div>
                <div className="relative">
                  <Lock size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted2" />
                  <input type={showPw ? 'text' : 'password'} className="input pl-9 pr-10" placeholder="••••••••"
                    value={password} onChange={e => setPassword(e.target.value)} required />
                  <button type="button" onClick={() => setShowPw(!showPw)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted2 hover:text-muted">
                    {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full justify-center mt-1">
                {loading ? <Spinner size={4} /> : <><span>Sign In</span><ArrowRight size={14} /></>}
              </button>
            </form>
          )}

          {tab === 'register' && (
            <form onSubmit={handleRegister} className="space-y-3">
              <div>
                <label className="label">Full Name *</label>
                <input type="text" className="input" placeholder="Priya Sharma"
                  value={reg.full_name} onChange={e => setReg({...reg, full_name: e.target.value})} required />
              </div>
              <div>
                <label className="label">Email *</label>
                <input type="email" className="input" placeholder="priya@college.edu"
                  value={reg.email} onChange={e => setReg({...reg, email: e.target.value})} required />
              </div>
              <div>
                <label className="label">Password *</label>
                <div className="relative">
                  <input type={showPw ? 'text' : 'password'} className="input pr-10" placeholder="Min 8 characters"
                    value={reg.password} onChange={e => setReg({...reg, password: e.target.value})} required />
                  <button type="button" onClick={() => setShowPw(!showPw)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted2 hover:text-muted">
                    {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">College</label>
                  <input type="text" className="input" placeholder="NIT Trichy"
                    value={reg.college} onChange={e => setReg({...reg, college: e.target.value})} />
                </div>
                <div>
                  <label className="label">Branch</label>
                  <input type="text" className="input" placeholder="CSE"
                    value={reg.branch} onChange={e => setReg({...reg, branch: e.target.value})} />
                </div>
                <div>
                  <label className="label">Grad Year</label>
                  <select className="input" value={reg.graduation_year}
                    onChange={e => setReg({...reg, graduation_year: e.target.value})}>
                    <option value="">Select</option>
                    {['2024','2025','2026','2027','2028'].map(y => <option key={y}>{y}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label">CGPA</label>
                  <input type="text" className="input" placeholder="8.5"
                    value={reg.cgpa} onChange={e => setReg({...reg, cgpa: e.target.value})} />
                </div>
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full justify-center mt-1">
                {loading ? <Spinner size={4} /> : <><span>Create Account</span><ArrowRight size={14} /></>}
              </button>
            </form>
          )}

          <p className="text-xs font-mono text-muted2 text-center mt-5">
            <button onClick={() => navigate('/')} className="text-muted hover:text-paper underline underline-offset-2">
              browse without signing in
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}
