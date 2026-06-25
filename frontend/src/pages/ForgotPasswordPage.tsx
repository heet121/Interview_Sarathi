// src/pages/ForgotPasswordPage.tsx
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Mail, ArrowLeft, CheckCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { authApi, errMsg } from '@/lib/api'
import { Spinner } from '@/components/ui'

export default function ForgotPasswordPage() {
  const [email,   setEmail]   = useState('')
  const [loading, setLoading] = useState(false)
  const [sent,    setSent]    = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await authApi.forgotPassword(email)
      setSent(true)
    } catch (e) { toast.error(errMsg(e)) }
    finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen bg-bg grid-bg flex items-center justify-center p-6">
      <div className="w-full max-w-sm fade-up card p-8 shadow-brutal">
        <Link to="/login" className="inline-flex items-center gap-1.5 text-xs font-mono text-muted
          hover:text-paper mb-8 transition-colors no-underline">
          <ArrowLeft size={13} /> back_to_sign_in
        </Link>

        {!sent ? (
          <>
            <div className="w-12 h-12 bg-acid/10 border-2 border-acid/30
              flex items-center justify-center mb-5">
              <Mail size={22} className="text-acid" />
            </div>
            <p className="nb-eyebrow mb-2">// reset</p>
            <h1 className="text-2xl text-paper mb-2">Reset your password</h1>
            <p className="text-sm text-muted mb-6 leading-relaxed">
              Enter your email and we'll send a reset link if the account exists.
            </p>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="label">Email address</label>
                <input type="email" className="input" placeholder="you@college.edu"
                  value={email} onChange={e => setEmail(e.target.value)} required />
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full justify-center">
                {loading ? <Spinner size={4} /> : 'Send Reset Link'}
              </button>
            </form>
          </>
        ) : (
          <div className="text-center">
            <CheckCircle size={48} className="text-ok mx-auto mb-4" />
            <h2 className="text-xl text-paper mb-2">Check your email</h2>
            <p className="text-sm text-muted leading-relaxed mb-6">
              If <strong className="text-paper">{email}</strong> is registered, a reset link has been sent. Check your spam folder too.
            </p>
            <Link to="/login" className="btn-ghost w-full justify-center no-underline">
              Back to sign in
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
