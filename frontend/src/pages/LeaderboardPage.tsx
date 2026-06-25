// src/pages/LeaderboardPage.tsx
import { useEffect, useState } from 'react'
import { Trophy, Zap, Star } from 'lucide-react'
import toast from 'react-hot-toast'
import { leaderboardApi, LeaderboardEntry } from '@/lib/api'
import { useAuth } from '@/context/AuthContext'
import Navbar from '@/components/layout/Navbar'
import { Spinner } from '@/components/ui'

type Period = 'weekly' | 'monthly' | 'all_time' | 'college'

const TABS: { key: Period; label: string }[] = [
  { key: 'weekly',   label: 'This Week'  },
  { key: 'monthly',  label: 'This Month' },
  { key: 'all_time', label: 'All Time'   },
  { key: 'college',  label: 'My College' },
]

const MEDAL = ['01','02','03']

export default function LeaderboardPage() {
  const { user }     = useAuth()
  const [tab,        setTab]     = useState<Period>('weekly')
  const [entries,    setEntries] = useState<LeaderboardEntry[]>([])
  const [myEntry,    setMyEntry] = useState<LeaderboardEntry | null>(null)
  const [loading,    setLoading] = useState(true)
  const [myRanks,    setMyRanks] = useState<any>(null)

  const load = async (period: Period) => {
    setLoading(true); setEntries([])
    try {
      let res: any
      if (period === 'weekly')   res = await leaderboardApi.weekly()
      if (period === 'monthly')  res = await leaderboardApi.monthly()
      if (period === 'all_time') res = await leaderboardApi.allTime()
      if (period === 'college')  res = await leaderboardApi.college()
      setEntries(res.data.leaderboard || [])
      setMyEntry(res.data.my_entry || null)
    } catch (e: any) {
      if (e.response?.status === 400 || e.response?.status === 422)
        toast.error(e.response?.data?.message || 'Set your college in profile to see college rankings')
      else toast.error('Failed to load leaderboard')
    } finally { setLoading(false) }
  }

  useEffect(() => { load(tab) }, [tab])

  useEffect(() => {
    leaderboardApi.myRanks().then(r => setMyRanks(r.data)).catch(() => {})
  }, [])

  const rankColor = (rank: number) =>
    rank === 1 ? 'text-warn' : rank === 2 ? 'text-[#d1d5db]' : rank === 3 ? 'text-[#cd7c32]' : 'text-muted2'

  return (
    <div className="min-h-screen bg-bg grid-bg">
      <Navbar />
      <div className="max-w-[900px] mx-auto px-5 py-10">

        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-none bg-[#fbbf24]/10 border border-warn/30
            flex items-center justify-center">
            <Trophy size={18} className="text-warn" />
          </div>
          <div>
            <p className="nb-eyebrow mb-1">// rankings</p>
            <h1 className="text-2xl text-paper">Leaderboard</h1>
          </div>
        </div>

        {/* My rank summary */}
        {myRanks && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            {[
              { lbl: 'Weekly Rank',   val: myRanks.weekly?.rank   ? `#${myRanks.weekly.rank}`   : '—', sub: myRanks.weekly?.percentile   ? `Top ${100 - myRanks.weekly.percentile}%`   : '' },
              { lbl: 'Monthly Rank',  val: myRanks.monthly?.rank  ? `#${myRanks.monthly.rank}`  : '—', sub: myRanks.monthly?.percentile  ? `Top ${100 - myRanks.monthly.percentile}%`  : '' },
              { lbl: 'All-Time Rank', val: myRanks.all_time?.rank ? `#${myRanks.all_time.rank}` : '—', sub: myRanks.all_time?.percentile ? `Top ${100 - myRanks.all_time.percentile}%` : '' },
              { lbl: 'Total Points',  val: myRanks.points || 0,   sub: `${myRanks.badges} badges · ${myRanks.streak}d streak` },
            ].map(s => (
              <div key={s.lbl} className="card p-4 text-center">
                <p className="text-[10px] font-mono uppercase tracking-widest text-muted2 mb-1">{s.lbl}</p>
                <p className="font-mono text-2xl text-acid">{s.val}</p>
                {s.sub && <p className="text-[10px] text-muted mt-0.5">{s.sub}</p>}
              </div>
            ))}
          </div>
        )}

        {/* Period tabs */}
        <div className="flex border-2 border-line mb-5">
          {TABS.map(t => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`flex-1 py-2.5 font-mono text-xs font-bold uppercase tracking-wide transition-colors
                ${tab === t.key ? 'bg-acid text-ink' : 'bg-s1 text-muted hover:text-paper'}`}>
              {t.label}
            </button>
          ))}
        </div>

        {/* Table */}
        <div className="card overflow-hidden">
          {/* Header */}
          <div className="grid grid-cols-[40px_1fr_80px_80px_70px] gap-3 px-5 py-3
            border-b border-line bg-s1">
            {['#','Name','Avg Score','Sessions','Points'].map(h => (
              <span key={h} className="text-[10px] font-mono uppercase tracking-widest text-muted2">
                {h}
              </span>
            ))}
          </div>

          {loading ? (
            <div className="flex justify-center py-16"><Spinner size={6} /></div>
          ) : entries.length === 0 ? (
            <div className="text-center py-16">
              <p className="text-sm text-muted">No entries yet for this period.</p>
              {tab === 'college' && !user?.college && (
                <p className="text-xs text-muted2 mt-2">
                  Add your college in{' '}
                  <a href="/profile" className="text-acid no-underline">Profile</a> to see rankings.
                </p>
              )}
            </div>
          ) : (
            <div className="divide-y divide-line/60">
              {entries.map((e, i) => (
                <div key={e.user_id}
                  className={`grid grid-cols-[40px_1fr_80px_80px_70px] gap-3 px-5 py-3.5 items-center
                    ${e.is_me ? 'bg-acid/[0.06] border-l-2 border-l-acid' : 'hover:bg-white/[0.02]'}
                    transition-colors`}>

                  {/* Rank */}
                  <span className={`font-mono text-sm font-bold ${rankColor(e.rank)}`}>
                    {i < 3 ? MEDAL[i] : `#${e.rank}`}
                  </span>

                  {/* Name */}
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="w-8 h-8 bg-acid border-2 border-ink
                      flex items-center justify-center text-[11px] font-bold text-ink shrink-0 font-mono">
                      {e.avatar_initial}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-white truncate flex items-center gap-1">
                        {e.full_name}
                        {e.is_me && <span className="text-[9px] chip-gold">You</span>}
                      </p>
                      {e.college && (
                        <p className="text-[10px] text-muted2 truncate">{e.college}</p>
                      )}
                    </div>
                  </div>

                  {/* Avg score */}
                  <span className={`text-sm font-semibold font-mono
                    ${e.avg_score >= 80 ? 'text-ok' : e.avg_score >= 60 ? 'text-warn' : 'text-bad'}`}>
                    {e.avg_score}
                  </span>

                  {/* Sessions */}
                  <span className="text-sm text-muted">{e.sessions_count}</span>

                  {/* Points */}
                  <div className="flex items-center gap-1">
                    <Star size={10} className="text-warn shrink-0" />
                    <span className="text-sm text-warn font-mono">{e.points}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* My entry sticky footer */}
        {myEntry && !entries.find(e => e.is_me) && (
          <div className="mt-4 card p-4 border-acid/30 bg-acid/[0.04]">
            <p className="text-xs text-muted mb-1">Your rank (not in top 50)</p>
            <div className="flex items-center gap-3">
              <span className="font-mono text-sm text-acid">#{myEntry.rank}</span>
              <span className="text-sm text-white">{myEntry.full_name}</span>
              <span className="text-sm text-ok ml-auto">{myEntry.avg_score} avg</span>
              <span className="text-sm text-warn">{myEntry.points} pts</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
