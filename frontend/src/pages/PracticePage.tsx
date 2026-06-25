// src/pages/PracticePage.tsx
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, X, ChevronRight } from 'lucide-react'
import toast from 'react-hot-toast'
import { interviewApi, sessionsApi, resumeApi, errMsg } from '@/lib/api'
import Navbar from '@/components/layout/Navbar'
import { Spinner } from '@/components/ui'

const ROLES = ['Software Engineer','Product Manager','Data Analyst','Data Scientist','Frontend Developer','Backend Developer','DevOps Engineer','System Design']
const TYPES = ['Technical','HR / Behavioral','Mixed','System Design']
const DIFFS = ['Beginner','Intermediate','Advanced']

export default function PracticePage() {
  const navigate = useNavigate()
  const [companies, setCompanies] = useState<string[]>([])
  const [loading,   setLoading]   = useState(false)

  const [form, setForm] = useState({
    company: 'Google', role: 'Software Engineer',
    interview_type: 'Technical', difficulty: 'Intermediate',
    num_questions: 5, skills_focus: '', custom_focus: '',
    custom_role: '', custom_company: '',
  })
  const [resumeFile, setResumeFile] = useState<File | null>(null)
  const [resumeText, setResumeText] = useState('')
  const [uploading,  setUploading]  = useState(false)

  useEffect(() => {
    interviewApi.companies()
      .then(r => setCompanies(r.data.companies.slice(0, 12)))
      .catch(() => setCompanies(['Google','Amazon','Microsoft','Infosys','TCS','Wipro','Flipkart','Razorpay','Swiggy','Zomato']))
    // Auto-load latest resume from DB
    resumeApi.latest()
      .then(r => { if (r.data?.text_content) setResumeText(r.data.text_content) })
      .catch(() => {})
  }, [])

  const handleResumeUpload = async (file: File) => {
    setResumeFile(file); setUploading(true)
    try {
      const res = await resumeApi.upload(file)
      // After upload, fetch full text
      const latest = await resumeApi.latest()
      if (latest.data?.text_content) setResumeText(latest.data.text_content)
      if (res.data.skills_extracted?.length)
        setForm(f => ({ ...f, skills_focus: res.data.skills_extracted!.slice(0, 6).join(', ') }))
      toast.success(`Resume parsed! Found ${res.data.skills_extracted?.length || 0} skills.`)
    } catch (e) { toast.error(errMsg(e)) }
    finally { setUploading(false) }
  }

  const handleStart = async () => {
    const role    = form.custom_role    || form.role
    const company = form.custom_company || form.company
    if (!role || !company) return toast.error('Please select a role and company')
    setLoading(true)
    try {
      const sessRes = await sessionsApi.create({
        company, role,
        interview_type: form.interview_type,
        difficulty:     form.difficulty,
        num_questions:  form.num_questions,
        skills_focus:   form.skills_focus || undefined,
        custom_focus:   form.custom_focus || undefined,
      })
      navigate(`/interview/${sessRes.data.id}`, {
        state: { resumeText, config: { ...form, role, company } },
      })
    } catch (e) { toast.error(errMsg(e)) }
    finally { setLoading(false) }
  }

  const Chip = ({ val, active, onClick }: { val: string; active: boolean; onClick: () => void }) => (
    <button key={val} onClick={onClick} type="button"
      className={`px-3 py-1.5 text-sm font-mono font-bold border-2 transition-all duration-100
        ${active
          ? 'bg-acid border-ink text-ink shadow-[2px_2px_0_0_#0b0b0e]'
          : 'bg-s2 border-line text-muted hover:border-acid hover:text-acid'
        }`}>
      {val}
    </button>
  )

  return (
    <div className="min-h-screen bg-bg grid-bg">
      <Navbar />
      <div className="max-w-[780px] mx-auto px-5 py-10">
        <p className="nb-eyebrow mb-2">// setup</p>
        <h1 className="text-3xl text-paper mb-1">Configure Your Interview</h1>
        <p className="text-sm text-muted mb-8">The AI personalises every question around your background and role.</p>

        {/* ── Resume ── */}
        <div className="card p-6 mb-4">
          <h3 className="text-sm font-bold font-mono uppercase tracking-wider text-paper mb-4">resume.upload()</h3>
          <label
            className="block border-2 border-dashed border-line p-6 text-center
              cursor-pointer hover:border-acid/40 hover:bg-acid/[0.04] transition-all"
            onDragOver={e => e.preventDefault()}
            onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleResumeUpload(f) }}>
            <input type="file" className="hidden" accept=".pdf,.doc,.docx,.txt"
              onChange={e => { const f = e.target.files?.[0]; if (f) handleResumeUpload(f) }} />
            {uploading ? (
              <div className="flex items-center justify-center gap-2 text-sm text-muted">
                <Spinner size={4} /> Parsing resume…
              </div>
            ) : resumeFile ? (
              <div className="flex items-center justify-center gap-2">
                <span className="text-ok text-sm font-medium">✓ {resumeFile.name}</span>
                <button type="button" onClick={e => { e.preventDefault(); setResumeFile(null); setResumeText('') }}>
                  <X size={14} className="text-muted hover:text-white" />
                </button>
              </div>
            ) : resumeText ? (
              <div className="text-ok text-sm">✓ Resume loaded from your profile</div>
            ) : (
              <>
                <Upload size={22} className="text-muted mx-auto mb-2" />
                <p className="text-sm font-medium text-white mb-1">Drop your resume or click to browse</p>
                <p className="text-xs text-muted2">PDF, DOC, DOCX, TXT · Max 10 MB</p>
              </>
            )}
          </label>
          {!resumeText && (
            <div className="mt-3">
              <label className="label">Or paste resume text</label>
              <textarea className="input min-h-[80px] resize-y" placeholder="Paste your resume content here…"
                value={resumeText} onChange={e => setResumeText(e.target.value)} />
            </div>
          )}
        </div>

        {/* ── Interview config ── */}
        <div className="card p-6 mb-4">
          <h3 className="text-sm font-bold font-mono uppercase tracking-wider text-paper mb-5">interview.config()</h3>
          <div className="space-y-5">

            <div>
              <label className="label">Target Company</label>
              <div className="flex flex-wrap gap-2 mb-2">
                {companies.map(c => (
                  <Chip key={c} val={c} active={form.company === c && !form.custom_company}
                    onClick={() => setForm({...form, company: c, custom_company: ''})} />
                ))}
              </div>
              <input className="input" placeholder="Or type another company…"
                value={form.custom_company} onChange={e => setForm({...form, custom_company: e.target.value})} />
            </div>

            <div>
              <label className="label">Target Role</label>
              <div className="flex flex-wrap gap-2 mb-2">
                {ROLES.map(r => (
                  <Chip key={r} val={r} active={form.role === r && !form.custom_role}
                    onClick={() => setForm({...form, role: r, custom_role: ''})} />
                ))}
              </div>
              <input className="input" placeholder="Or type a custom role…"
                value={form.custom_role} onChange={e => setForm({...form, custom_role: e.target.value})} />
            </div>

            <div>
              <label className="label">Interview Type</label>
              <div className="flex flex-wrap gap-2">
                {TYPES.map(t => (
                  <Chip key={t} val={t} active={form.interview_type === t}
                    onClick={() => setForm({...form, interview_type: t})} />
                ))}
              </div>
            </div>

            <div>
              <label className="label">Difficulty</label>
              <div className="flex gap-2">
                {DIFFS.map(d => (
                  <Chip key={d} val={d} active={form.difficulty === d}
                    onClick={() => setForm({...form, difficulty: d})} />
                ))}
              </div>
            </div>

            <div>
              <label className="label">Number of Questions: {form.num_questions}</label>
              <input type="range" min={3} max={8} value={form.num_questions}
                onChange={e => setForm({...form, num_questions: +e.target.value})}
                className="w-full h-1 rounded bg-[#1e1e30] appearance-none cursor-pointer accent-acid" />
              <div className="flex justify-between text-[10px] text-muted2 mt-1">
                <span>3 (quick)</span><span>8 (full round)</span>
              </div>
            </div>

            <div>
              <label className="label">Key Skills to Focus On</label>
              <input className="input" placeholder="e.g. Python, React, SQL, System Design, DSA"
                value={form.skills_focus} onChange={e => setForm({...form, skills_focus: e.target.value})} />
            </div>

            <div>
              <label className="label">Custom Instructions (optional)</label>
              <textarea className="input min-h-[60px] resize-none"
                placeholder="e.g. Ask about my food delivery project, focus more on STAR format…"
                value={form.custom_focus} onChange={e => setForm({...form, custom_focus: e.target.value})} />
            </div>
          </div>
        </div>

        <button onClick={handleStart} disabled={loading}
          className="btn-primary w-full justify-center text-base py-4">
          {loading
            ? <><Spinner size={4} /> Setting up your interview…</>
            : <>Start AI Interview <ChevronRight size={18} /></>
          }
        </button>
      </div>
    </div>
  )
}
