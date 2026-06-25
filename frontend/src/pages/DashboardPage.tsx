// src/pages/DashboardPage.tsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { BarChart2, Zap, Trophy, TrendingUp, ArrowRight, Terminal } from 'lucide-react'
import { dashboardApi, DashboardData } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import Navbar from '@/components/layout/Navbar'
import { Spinner, ProgressBar } from '@/components/ui'
import toast from 'react-hot-toast'

export default function DashboardPage() {
  const { user } = useAuth()
  const [data,    setData]    = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    dashboardApi.me()
      .then(r => setData(r.data))
      .catch(() => toast.error('Failed to load dashboard'))
      .finally(() => setLoading(false))
  }, [])

  const sc = (s: number) => s >= 80 ? 'text-ok' : s >= 60 ? 'text-warn' : 'text-bad'

  return (
    <div className="min-h-screen bg-bg grid-bg">
      <Navbar />
      <div className="max-w-[1200px] mx-auto px-5 py-10">

        {/* Header */}
        <div className="flex items-start justify-between mb-8 gap-4">
          <div>
            <p className="nb-eyebrow mb-2">// dashboard</p>
            <h1 className="text-3xl text-paper">
              Welcome back,{' '}
              <em className="text-acid not-italic">
                {user?.full_name?.split(' ')[0] || 'there'}
              </em>
            </h1>
            {(user?.college || user?.branch) && (
              <p className="text-sm text-muted mt-1">
                {[user?.college, user?.branch].filter(Boolean).join(' · ')}
              </p>
            )}
          </div>
          <Link to="/practice" className="btn-primary shrink-0 hidden sm:inline-flex">
            New Interview <ArrowRight size={14} />
          </Link>
        </div>

        {loading ? (
          <div className="flex justify-center py-24"><Spinner size={8} /></div>
        ) : !data ? (
          <div className="text-center py-24 text-muted">Failed to load dashboard.</div>
        ) : data.summary.total_sessions === 0 ? (
          /* ── Empty state ── */
          <div className="text-center py-24 card p-10 max-w-md mx-auto shadow-brutal">
            <div className="w-14 h-14 bg-acid border-2 border-ink mx-auto mb-4 flex items-center justify-center shadow-[3px_3px_0_0_#0b0b0e]">
              <Terminal size={24} className="text-ink" />
            </div>
            <h2 className="text-2xl text-paper mb-2">No interviews yet</h2>
            <p className="text-sm text-muted mb-6">Start your first mock interview to see your analytics here.</p>
            <Link to="/practice" className="btn-primary no-underline">
              Start Your First Interview →
            </Link>
          </div>
        ) : (
          <>
            {/* ── Stats row ── */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              {[
                { icon: BarChart2,  val: data.summary.total_sessions, suffix: '',   lbl: 'Interviews Done',    color: 'text-acid' },
                { icon: TrendingUp, val: data.summary.avg_score,      suffix: '',   lbl: 'Avg Score',          color: 'text-ok' },
                { icon: Zap,        val: data.user.streak,            suffix: 'd',  lbl: 'Current Streak',     color: 'text-cyan' },
                { icon: Trophy,     val: data.user.total_points,      suffix: ' pts',lbl: 'Total Points',      color: 'text-warn' },
              ].map(s => (
                <div key={s.lbl} className="card p-5">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[10px] font-mono uppercase tracking-widest text-muted2">{s.lbl}</span>
                    <s.icon size={14} className={s.color} />
                  </div>
                  <div className={`font-mono text-3xl font-bold ${s.color}`}>
                    {typeof s.val === 'number' ? Math.round(s.val) : s.val}{s.suffix}
                  </div>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-5">

              {/* ── Recent sessions ── */}
              <div className="lg:col-span-2 card overflow-hidden">
                <div className="flex items-center justify-between px-5 py-4 border-b border-line">
                  <h2 className="text-sm font-semibold text-white">Recent Sessions</h2>
                  <Link to="/sessions" className="text-xs text-acid hover:text-acid2 no-underline">View all →</Link>
                </div>
                <div className="divide-y divide-line/60">
                  {data.recent_sessions.length === 0 ? (
                    <p className="px-5 py-8 text-sm text-muted text-center">No completed sessions yet.</p>
                  ) : data.recent_sessions.map(s => (
                    <Link key={s.id} to={`/sessions/${s.id}`}
                      className="flex items-center gap-4 px-5 py-3.5 hover:bg-white/[0.02] transition-colors no-underline group">
                      <div className="w-9 h-9 bg-s2 border-2 border-line
                        flex items-center justify-center shrink-0 font-mono text-[10px] font-bold text-acid">
                        {s.company.slice(0, 2).toUpperCase()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-white truncate">{s.company} — {s.role}</p>
                        <p className="text-[11px] text-muted mt-0.5">
                          {s.interview_type} · {s.difficulty} ·{' '}
                          {new Date(s.completed_at).toLocaleDateString('en-IN',{day:'numeric',month:'short'})}
                        </p>
                      </div>
                      <div className="shrink-0 flex items-center gap-2">
                        <span className={`font-mono text-xl ${sc(s.score)}`}>{Math.round(s.score)}</span>
                        {s.verdict && (
                          <span className={`chip text-[9px] ${s.verdict === 'Excellent' ? 'chip-green' : s.verdict === 'Good' ? 'chip-teal' : 'chip-amber'}`}>
                            {s.verdict}
                          </span>
                        )}
                      </div>
                    </Link>
                  ))}
                </div>
              </div>

              {/* ── Dimension averages + badges ── */}
              <div className="space-y-4">
                {Object.keys(data.dimension_averages).length > 0 && (
                  <div className="card p-5">
                    <h3 className="text-sm font-semibold text-white mb-4">Skill Averages</h3>
                    {Object.entries(data.dimension_averages).map(([k, v]) => (
                      <div key={k} className="mb-3">
                        <div className="flex justify-between text-xs text-muted mb-1.5">
                          <span>{k}</span>
                          <span className={sc(v)}>{v}</span>
                        </div>
                        <ProgressBar value={v}
                          color={v >= 80 ? '#4ade80' : v >= 60 ? '#fbbf24' : '#f87171'} />
                      </div>
                    ))}
                  </div>
                )}

                {data.badges.earned_count > 0 && (
                  <div className="card p-5">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-semibold text-white">Badges</h3>
                      <Link to="/profile#badges" className="text-xs text-acid no-underline">
                        {data.badges.earned_count}/{data.badges.total_available}
                      </Link>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {data.badges.earned.slice(0, 8).map(b => (
                        <span key={b.key} title={b.name} className="text-xl">{b.emoji}</span>
                      ))}
                    </div>
                  </div>
                )}

                {data.top_companies.length > 0 && (
                  <div className="card p-5">
                    <h3 className="text-sm font-semibold text-white mb-3">Top Companies</h3>
                    {data.top_companies.slice(0, 4).map(c => (
                      <div key={c.company} className="flex items-center justify-between py-2
                        border-b border-line/60 last:border-0">
                        <span className="text-sm text-paper">{c.company}</span>
                        <span className={`text-sm font-semibold ${sc(c.avg_score)}`}>{c.avg_score}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="sm:hidden">
              <Link to="/practice" className="btn-primary w-full justify-center no-underline">
                New Interview <ArrowRight size={14} />
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
