// src/pages/ProfilePage.tsx
import { useState, useEffect } from 'react'
import { Save, Lock, Trash2, Upload } from 'lucide-react'
import toast from 'react-hot-toast'
import { authApi, resumeApi, dashboardApi, errMsg, ResumeOut, BadgeItem } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import Navbar from '@/components/layout/Navbar'
import { Spinner } from '@/components/ui'

export default function ProfilePage() {
  const { user, refresh } = useAuth()
  const [saving,    setSaving]    = useState(false)
  const [pwSaving,  setPwSaving]  = useState(false)
  const [resumes,   setResumes]   = useState<ResumeOut[]>([])
  const [badges,    setBadges]    = useState<{ earned: BadgeItem[]; locked: BadgeItem[] } | null>(null)
  const [uploading, setUploading] = useState(false)

  const [form, setForm] = useState({
    full_name:       user?.full_name       || '',
    college:         user?.college         || '',
    branch:          user?.branch          || '',
    graduation_year: user?.graduation_year || '',
    cgpa:            user?.cgpa            || '',
  })
  const [pw, setPw] = useState({ current: '', next: '', confirm: '' })

  useEffect(() => {
    resumeApi.list().then(r => setResumes(r.data)).catch(() => {})
    dashboardApi.badges().then(r => setBadges(r.data)).catch(() => {})
  }, [])

  // Keep form in sync if user changes
  useEffect(() => {
    if (user) setForm({
      full_name: user.full_name || '', college: user.college || '',
      branch: user.branch || '', graduation_year: user.graduation_year || '', cgpa: user.cgpa || '',
    })
  }, [user])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await authApi.updateMe(form)
      await refresh()
      toast.success('Profile updated')
    } catch (e) { toast.error(errMsg(e)) }
    finally { setSaving(false) }
  }

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault()
    if (pw.next !== pw.confirm) return toast.error('Passwords do not match')
    if (pw.next.length < 8)    return toast.error('Password must be at least 8 characters')
    setPwSaving(true)
    try {
      await authApi.changePassword(pw.current, pw.next)
      toast.success('Password updated')
      setPw({ current: '', next: '', confirm: '' })
    } catch (e) { toast.error(errMsg(e)) }
    finally { setPwSaving(false) }
  }

  const handleResumeUpload = async (file: File) => {
    setUploading(true)
    try {
      await resumeApi.upload(file)
      const res = await resumeApi.list()
      setResumes(res.data)
      toast.success('Resume uploaded!')
    } catch (e) { toast.error(errMsg(e)) }
    finally { setUploading(false) }
  }

  const handleResumeDelete = async (id: number) => {
    try {
      await resumeApi.delete(id)
      setResumes(r => r.filter(x => x.id !== id))
      toast.success('Resume deleted')
    } catch (e) { toast.error(errMsg(e)) }
  }

  return (
    <div className="min-h-screen bg-bg grid-bg">
      <Navbar />
      <div className="max-w-[720px] mx-auto px-5 py-10">
        <p className="nb-eyebrow mb-2">// account</p>
        <h1 className="text-3xl text-paper mb-8">Your Profile</h1>

        <form onSubmit={handleSave} className="card p-6 mb-5">
          <h2 className="text-sm font-bold font-mono uppercase tracking-wider text-paper mb-5">
            user.profile()
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="label">Full Name</label>
              <input className="input" placeholder="Priya Sharma" value={form.full_name}
                onChange={e => setForm({...form, full_name: e.target.value})} />
            </div>
            <div className="col-span-2">
              <label className="label">Email (read-only)</label>
              <input className="input opacity-50 cursor-not-allowed" value={user?.email || ''} disabled />
            </div>
            <div>
              <label className="label">College</label>
              <input className="input" placeholder="NIT Trichy" value={form.college}
                onChange={e => setForm({...form, college: e.target.value})} />
            </div>
            <div>
              <label className="label">Branch</label>
              <input className="input" placeholder="CSE" value={form.branch}
                onChange={e => setForm({...form, branch: e.target.value})} />
            </div>
            <div>
              <label className="label">Graduation Year</label>
              <select className="input" value={form.graduation_year}
                onChange={e => setForm({...form, graduation_year: e.target.value})}>
                <option value="">Select</option>
                {['2024','2025','2026','2027','2028'].map(y => <option key={y}>{y}</option>)}
              </select>
            </div>
            <div>
              <label className="label">CGPA</label>
              <input className="input" placeholder="8.5" value={form.cgpa}
                onChange={e => setForm({...form, cgpa: e.target.value})} />
            </div>
          </div>
          <button type="submit" disabled={saving} className="btn-primary mt-5 flex items-center gap-2">
            {saving ? <Spinner size={3} /> : <><Save size={14} /> Save Changes</>}
          </button>
        </form>

        {/* ── Resume manager ── */}
        <div className="card p-6 mb-5">
          <h2 className="text-sm font-bold font-mono uppercase tracking-wider text-paper mb-4">
            resume.list()
          </h2>
          {resumes.length === 0 ? (
            <p className="text-sm text-muted mb-3">No resumes uploaded yet.</p>
          ) : (
            <div className="space-y-2 mb-4">
              {resumes.map(r => (
                <div key={r.id} className="flex items-center justify-between bg-s2
                  border border-line rounded-none px-4 py-3">
                  <div>
                    <p className="text-sm text-white font-medium">{r.filename || `Resume #${r.id}`}</p>
                    <p className="text-[11px] text-muted2 mt-0.5">
                      {r.skills_extracted?.slice(0,4).join(', ')}
                      {r.skills_extracted && r.skills_extracted.length > 4 ? ` +${r.skills_extracted.length - 4} more` : ''}
                    </p>
                  </div>
                  <button onClick={() => handleResumeDelete(r.id)}
                    className="text-bad/60 hover:text-bad transition-colors p-1">
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}
          <label className="btn-outline cursor-pointer flex items-center gap-2 w-fit">
            <input type="file" className="hidden" accept=".pdf,.doc,.docx,.txt"
              onChange={e => { const f = e.target.files?.[0]; if (f) handleResumeUpload(f) }} />
            {uploading ? <Spinner size={3} /> : <Upload size={14} />}
            Upload New Resume
          </label>
        </div>

        {/* ── Change Password ── */}
        <form onSubmit={handlePasswordChange} className="card p-6 mb-5">
          <h2 className="text-sm font-semibold text-white mb-5 flex items-center gap-2">
            <Lock size={14} /> Change Password
          </h2>
          <div className="space-y-4">
            <div>
              <label className="label">Current Password</label>
              <input type="password" className="input" value={pw.current}
                onChange={e => setPw({...pw, current: e.target.value})} required />
            </div>
            <div>
              <label className="label">New Password</label>
              <input type="password" className="input" value={pw.next}
                onChange={e => setPw({...pw, next: e.target.value})} required />
            </div>
            <div>
              <label className="label">Confirm New Password</label>
              <input type="password" className="input" value={pw.confirm}
                onChange={e => setPw({...pw, confirm: e.target.value})} required />
            </div>
          </div>
          <button type="submit" disabled={pwSaving} className="btn-outline mt-5 flex items-center gap-2">
            {pwSaving ? <Spinner size={3} /> : <><Lock size={14} /> Update Password</>}
          </button>
        </form>

        {/* ── Badges ── */}
        {badges && (
          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold font-mono uppercase tracking-wider text-paper flex items-center gap-2">
                badges.earned()
              </h2>
              <span className="text-xs text-muted">
                {badges.earned.length} / {badges.earned.length + badges.locked.length} earned
              </span>
            </div>

            {badges.earned.length > 0 && (
              <>
                <p className="text-[11px] font-mono uppercase tracking-wider text-muted2 mb-3">Earned</p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-5">
                  {badges.earned.map(b => (
                    <div key={b.key} className="bg-acid/[0.06] border border-acid/20
                      rounded-none p-3 flex flex-col items-center text-center gap-1">
                      <span className="text-2xl">{b.emoji}</span>
                      <p className="text-xs font-semibold text-white">{b.name}</p>
                      <p className="text-[10px] text-muted">{b.description}</p>
                      <span className="chip-gold text-[9px]">+{b.points} pts</span>
                    </div>
                  ))}
                </div>
              </>
            )}

            {badges.locked.length > 0 && (
              <>
                <p className="text-[11px] font-mono uppercase tracking-wider text-muted2 mb-3">Locked</p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {badges.locked.slice(0, 6).map(b => (
                    <div key={b.key} className="bg-s1 border border-line
                      rounded-none p-3 flex flex-col items-center text-center gap-1 opacity-60">
                      <span className="text-2xl grayscale">{b.emoji}</span>
                      <p className="text-xs font-semibold text-muted">{b.name}</p>
                      <p className="text-[10px] text-muted2">{b.hint || b.description}</p>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
