// src/pages/SessionPage.tsx
import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, RefreshCw, RotateCcw, Trash2, BookOpen, AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'
import { sessionsApi, analysisApi, errMsg, SessionDetail, AnalysisResult, SessionQuestion, JudgeScores } from '@/lib/api'
import Navbar from '@/components/layout/Navbar'
import { Spinner, ScoreRing, ProgressBar } from '@/components/ui'

// ── Helpers ───────────────────────────────────────────────────────────────────

function isSkipped(text: string | null | undefined): boolean {
  if (!text) return true
  const n = text.trim().toLowerCase()
  return n === '' || n === '[skipped]' || n === 'skipped' || n === 'n/a' || n === '-'
}

function answeredCount(questions: SessionQuestion[]): number {
  return questions.filter(q => !isSkipped(q.answer_text)).length
}

function getTopicsFromQuestion(questionText: string): string[] {
  const q = questionText.toLowerCase()
  const map: [RegExp, string[]][] = [
    [/array|list|tuple|vector|sequence/, ['Arrays & Lists', 'Time Complexity O(n)']],
    [/hash|dict|map|lookup|key.value/, ['Hash Maps / Dictionaries', 'O(1) Lookups']],
    [/tree|bst|binary|heap|trie/, ['Binary Trees', 'Tree Traversal (BFS/DFS)']],
    [/graph|node|edge|network|path/, ['Graph Theory', 'DFS & BFS', 'Shortest Path']],
    [/sort|order|quicksort|mergesort/, ['Sorting Algorithms', 'QuickSort vs MergeSort']],
    [/stack|queue|deque|lifo|fifo/, ['Stacks & Queues', 'Use Cases']],
    [/dynamic|dp|memoiz|tabulation/, ['Dynamic Programming', 'Memoization']],
    [/recursion|recursive|base case/, ['Recursion', 'Call Stack Mechanics']],
    [/big.o|complexity|time.space|optimize/, ['Big-O Notation', 'Algorithm Optimization']],
    [/link|linked list|pointer|node.next/, ['Linked Lists', 'Fast/Slow Pointer Technique']],
    [/design|architect|system|scale|distribut/, ['System Design', 'Scalability Patterns']],
    [/database|sql|nosql|postgres|mysql|mongo/, ['SQL vs NoSQL', 'Database Indexing', 'ACID']],
    [/cache|redis|memcache|cdn/, ['Caching Strategies', 'Redis Basics']],
    [/api|rest|graphql|endpoint|http/, ['REST API Design', 'HTTP Methods']],
    [/microservice|monolith|service|docker/, ['Microservices', 'Docker & Containers']],
    [/auth|jwt|oauth|session|token|login/, ['JWT Authentication', 'OAuth 2.0']],
    [/cloud|aws|azure|gcp|serverless/, ['Cloud Computing', 'AWS Core Services']],
    [/oop|class|object|inherit|polymorphi/, ['OOP Principles', 'Inheritance']],
    [/solid|principle|design.pattern/, ['SOLID Principles', 'Design Patterns']],
    [/test|unit.test|tdd|mock/, ['Unit Testing', 'Test-Driven Development']],
    [/python|decorator|generator|comprehension/, ['Python Advanced Concepts', 'Decorators']],
    [/javascript|async.await|promise|closure/, ['JavaScript Async/Await', 'Closures & Scope']],
    [/challeng|difficult|fail|mistake|learn/, ['STAR Method', 'Storytelling in Interviews']],
    [/conflict|disagree|team|collaborat/, ['Conflict Resolution', 'Communication Skills']],
    [/leader|mentor|initiative|owner/, ['Leadership Principles', 'Taking Ownership']],
    [/machine.learn|model|train|predict/, ['ML Fundamentals', 'Model Evaluation']],
    [/neural|deep.learn|cnn|rnn|transformer/, ['Neural Networks', 'Deep Learning Architecture']],
  ]
  const found: string[] = []
  for (const [pattern, topics] of map) {
    if (pattern.test(q)) {
      for (const t of topics) {
        if (!found.includes(t)) found.push(t)
      }
    }
    if (found.length >= 4) break
  }
  return found.length > 0 ? found : ['Core CS Fundamentals', 'Data Structures', 'Problem Solving']
}

const sc    = (s: number) => s >= 80 ? 'text-ok' : s >= 60 ? 'text-warn' : 'text-bad'
const scBar = (s: number) => s >= 80 ? '#4ade80' : s >= 60 ? '#fbbf24' : '#f87171'

const JUDGE_DIMS: { key: keyof JudgeScores; label: string }[] = [
  { key: 'relevance', label: 'Relevance' },
  { key: 'correctness', label: 'Correctness' },
  { key: 'depth', label: 'Depth' },
  { key: 'communication', label: 'Communication' },
  { key: 'structure', label: 'Structure' },
]

function JudgeBars({ scores, overall }: { scores?: Record<string, number>; overall?: number }) {
  if (!scores || !Object.keys(scores).length) return null
  return (
    <div className="mt-3 pt-3 border-t border-line">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-muted2">
          DeBERTa Judge
        </span>
        {overall != null && (
          <span className={`text-xs font-semibold ${sc(overall)}`}>{Math.round(overall)}/100</span>
        )}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {JUDGE_DIMS.map(({ key, label }) => {
          const v = scores[key]
          if (v == null) return null
          return (
            <div key={key}>
              <div className="flex justify-between text-[10px] mb-0.5">
                <span className="text-muted">{label}</span>
                <span className={sc(v)}>{Math.round(v)}</span>
              </div>
              <ProgressBar value={v} color={scBar(v)} />
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Skipped question study card ───────────────────────────────────────────────
function SkippedTopicsCard({ question, index }: { question: string; index: number }) {
  const topics = getTopicsFromQuestion(question)
  return (
    <div className="card p-5 border-bad/20">
      <div className="flex items-center gap-2 mb-3">
        <span className="chip bg-bad/10 text-bad border border-bad/30 text-[10px]">
          Q{index + 1} · Skipped
        </span>
        <AlertTriangle size={13} className="text-warn" />
      </div>
      <p className="text-sm font-semibold text-acid mb-3 leading-snug">{question}</p>
      <div className="bg-s1 rounded-none p-4 border border-line">
        <div className="flex items-center gap-2 mb-2.5">
          <BookOpen size={13} className="text-cyan" />
          <span className="text-[11px] font-semibold text-cyan uppercase tracking-wider">
            Study these topics to answer this confidently
          </span>
        </div>
        <ul className="space-y-1.5">
          {topics.map((t, i) => (
            <li key={i} className="flex items-center gap-2 text-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-[#2dd4bf]/60 shrink-0" />
              <span className="text-paper">{t}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function SessionPage() {
  const { id }    = useParams<{ id: string }>()
  const navigate  = useNavigate()
  const sessionId = Number(id)

  const [detail,    setDetail]    = useState<SessionDetail | null>(null)
  const [analysis,  setAnalysis]  = useState<AnalysisResult | null>(null)
  const [loading,   setLoading]   = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [deleting,  setDeleting]  = useState(false)

  useEffect(() => {
    if (!sessionId) return
    sessionsApi.get(sessionId)
      .then(async r => {
        setDetail(r.data)

        const qs            = r.data.questions ?? []
        const realAnswers   = answeredCount(qs)

        // Analysis already stored — use it directly
        if (r.data.analysis) {
          setAnalysis(r.data.analysis)
          setLoading(false)
          return
        }

        // Session not completed or no questions yet
        if (r.data.session.status !== 'completed' || qs.length === 0) {
          setLoading(false)
          return
        }

        // No real answers at all — do NOT call analysis API
        if (realAnswers === 0) {
          setLoading(false)
          return
        }

        // Has ≥1 real answer — auto-generate analysis
        setLoading(false)
        setAnalyzing(true)
        try {
          const res = await analysisApi.generate(sessionId)
          setAnalysis(res.data)
          toast.success('Analysis ready!')
        } catch {
          toast.error('Analysis generation failed — click Generate Analysis to retry')
        } finally {
          setAnalyzing(false)
        }
      })
      .catch(() => { toast.error('Session not found'); navigate('/dashboard') })
  }, [sessionId, navigate])

  const runAnalysis = async () => {
    setAnalyzing(true)
    try {
      const res = await analysisApi.generate(sessionId)
      setAnalysis(res.data)
      toast.success('Analysis ready!')
    } catch (e) { toast.error(errMsg(e)) }
    finally { setAnalyzing(false) }
  }

  const handleDelete = async () => {
    if (!confirm('Delete this session permanently?')) return
    setDeleting(true)
    try {
      await sessionsApi.delete(sessionId)
      toast.success('Session deleted')
      navigate('/dashboard')
    } catch (e) { toast.error(errMsg(e)) }
    finally { setDeleting(false) }
  }

  const sess         = detail?.session
  const questions    = detail?.questions ?? []
  const totalAnswered = answeredCount(questions)
  const totalSkipped  = questions.filter(q => isSkipped(q.answer_text)).length
  const noRealAnswers = sess?.status === 'completed' && questions.length > 0 && totalAnswered === 0

  if (loading) {
    return (
      <div className="min-h-screen bg-bg grid-bg">
        <Navbar />
        <div className="flex justify-center py-32"><Spinner size={8} /></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-bg grid-bg">
      <Navbar />
      <div className="max-w-[1060px] mx-auto px-5 py-10">

        <Link to="/dashboard"
          className="inline-flex items-center gap-1.5 text-xs text-muted
            hover:text-white mb-6 transition-colors no-underline">
          <ArrowLeft size={13} /> Dashboard
        </Link>

        {/* ── Session header card ── */}
        {sess && (
          <div className="card p-6 mb-5 flex items-center justify-between gap-4 flex-wrap">
            <div>
              <p className="text-[11px] font-mono uppercase tracking-widest text-muted2 mb-1">
                Session Report
              </p>
              <h1 className="text-2xl text-white">{sess.company} — {sess.role}</h1>
              <p className="text-sm text-muted mt-1">
                {sess.interview_type} · {sess.difficulty} ·{' '}
                {sess.started_at && new Date(sess.started_at).toLocaleDateString('en-IN', {
                  day: 'numeric', month: 'long', year: 'numeric',
                })}
              </p>
              <div className="flex flex-wrap gap-2 mt-2">
                <span className={`chip text-[10px] ${sess.status === 'completed' ? 'chip-green' : 'chip-amber'}`}>
                  {sess.status}
                </span>
                {sess.num_questions && (
                  <span className="chip bg-white/5 text-muted border-0 text-[10px]">
                    {sess.num_questions} questions
                  </span>
                )}
                {totalAnswered > 0 && (
                  <span className="chip bg-[#4ade80]/10 text-ok border border-[#4ade80]/20 text-[10px]">
                    {totalAnswered} answered
                  </span>
                )}
                {totalSkipped > 0 && (
                  <span className="chip bg-bad/10 text-bad border border-bad/30 text-[10px]">
                    {totalSkipped} skipped
                  </span>
                )}
              </div>
            </div>

            <div className="flex items-center gap-3">
              {analysis
                ? <ScoreRing score={analysis.overall_score} size={90} />
                : (!noRealAnswers && sess.status === 'completed' && !analyzing && (
                  <button onClick={runAnalysis} disabled={analyzing} className="btn-primary">
                    <RefreshCw size={14} /> Generate Analysis
                  </button>
                ))
              }
              <div className="flex flex-col gap-1.5">
                <Link to="/practice" className="btn-outline text-xs no-underline justify-center">
                  <RotateCcw size={12} /> Practice Again
                </Link>
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="btn-outline text-xs text-bad border-bad/30
                    hover:border-[#f87171]/40 hover:bg-[#f87171]/5"
                >
                  {deleting ? <Spinner size={3} /> : <><Trash2 size={12} /> Delete</>}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── Generating spinner ── */}
        {analyzing && (
          <div className="card p-5 mb-4 border-cyan/30 flex items-center gap-3">
            <Spinner size={5} />
            <div>
              <p className="text-sm font-semibold text-white">Generating your analysis…</p>
              <p className="text-xs text-muted mt-0.5">AI is reviewing your answers. This takes 15–30 seconds.</p>
            </div>
          </div>
        )}

        {/* ════════════════════════════════════════════════════════
            CASE A: Completed, zero real answers
        ════════════════════════════════════════════════════════ */}
        {noRealAnswers && (
          <div className="space-y-5">
            <div className="card p-6 border-warn/30 bg-warn/[0.04]">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-none bg-[#fbbf24]/10 border border-warn/30
                  flex items-center justify-center shrink-0">
                  <AlertTriangle size={18} className="text-warn" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-white mb-1">Session Ended</h2>
                  <p className="text-sm text-muted leading-relaxed">
                    No answers were recorded in this session. Review the topics below for each
                    question you saw, then start a new session when you're ready.
                  </p>
                </div>
              </div>
            </div>

            {questions.length > 0 && (
              <>
                <div className="flex items-center gap-2 pt-1">
                  <BookOpen size={16} className="text-cyan" />
                  <h2 className="font-mono text-xl text-white">Topics to Study</h2>
                  <span className="chip-teal text-[10px] ml-1">{questions.length} questions</span>
                </div>
                <div className="space-y-3">
                  {questions.map((q, i) => (
                    <SkippedTopicsCard
                      key={q.question_index ?? i}
                      question={q.question_text ?? `Question ${i + 1}`}
                      index={i}
                    />
                  ))}
                </div>
              </>
            )}

            <div className="flex gap-3 mt-4">
              <Link to="/practice" className="btn-primary no-underline">Try Again →</Link>
              <Link to="/dashboard" className="btn-ghost no-underline">Dashboard</Link>
            </div>
          </div>
        )}

        {/* ════════════════════════════════════════════════════════
            CASE B: Full analysis available
        ════════════════════════════════════════════════════════ */}
        {!noRealAnswers && analysis && (
          <>
            {/* Verdict + summary + DeBERTa judge highlight */}
            <div className="card p-5 mb-4 border-acid/30 shadow-brutalA">
              <p className="nb-eyebrow mb-2">// analysis.report</p>
              <div className="flex items-center gap-3 mb-3 flex-wrap">
                <span className={`chip text-sm font-bold px-3 py-1.5 rounded-none
                  ${analysis.verdict === 'Excellent' ? 'chip-green' :
                    analysis.verdict === 'Good'      ? 'chip-teal'  :
                    analysis.verdict === 'Average'   ? 'chip-amber' : 'chip-red'}`}>
                  {analysis.verdict}
                </span>
                <span className={`font-mono text-2xl ${sc(analysis.overall_score)}`}>
                  {analysis.overall_score}/100
                </span>
                {(analysis as any).gamification?.points_earned
                  ? <span className="chip-gold">+{(analysis as any).gamification.points_earned} pts</span>
                  : null}
                {(analysis as any).skipped_count > 0 && (
                  <span className="chip bg-bad/10 text-bad border border-bad/30 text-[10px]">
                    {(analysis as any).skipped_count} skipped
                  </span>
                )}
              </div>
              <p className="text-sm text-paper leading-relaxed">{analysis.overall_summary}</p>

              {/* Average judge dimensions from Q&A */}
              {(() => {
                const withJudge = analysis.qa_breakdown.filter((q: any) => q.judge_scores && !q.skipped)
                if (!withJudge.length) return null
                const dims = ['relevance', 'correctness', 'depth', 'communication', 'structure'] as const
                const avgs = dims.map(d => {
                  const vals = withJudge.map((q: any) => q.judge_scores[d] as number).filter(Boolean)
                  return { d, v: vals.length ? Math.round(vals.reduce((a, b) => a + b, 0) / vals.length) : 0 }
                })
                const overall = Math.round(avgs.reduce((s, x) => s + x.v, 0) / avgs.length)
                return (
                  <div className="mt-4 pt-4 border-t-2 border-line">
                    <div className="flex items-center justify-between mb-3">
                      <span className="font-mono text-xs font-bold uppercase text-acid">DeBERTa Judge</span>
                      <span className={`font-mono text-lg font-bold ${sc(overall)}`}>{overall}/100</span>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                      {avgs.map(({ d, v }) => (
                        <div key={d} className="bg-s1 border border-line p-2">
                          <p className="text-[9px] font-mono uppercase text-muted2 mb-1">{d}</p>
                          <p className={`font-mono text-sm font-bold ${sc(v)}`}>{v}</p>
                          <ProgressBar value={v} color={scBar(v)} />
                        </div>
                      ))}
                    </div>
                  </div>
                )
              })()}

              {(analysis as any).gamification?.badges_earned?.length ? (
                <div className="flex items-center gap-2 mt-3 pt-3 border-t border-line">
                  <span className="text-xs text-muted">Badges earned:</span>
                  {(analysis as any).gamification.badges_earned.map((b: any) => (
                    <span key={b.name} title={b.name} className="text-xl">{b.emoji}</span>
                  ))}
                </div>
              ) : null}
            </div>

            {/* Dimensions + Strengths/Improvements */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              {Object.keys(analysis.dimensions).length > 0 && (
                <div className="card p-5">
                  <h3 className="text-sm font-bold font-mono uppercase tracking-wider text-paper mb-4">dimensions</h3>
                  {Object.entries(analysis.dimensions).map(([k, v]) => (
                    <div key={k} className="mb-3">
                      <div className="flex justify-between text-xs mb-1.5">
                        <span className="text-muted">{k}</span>
                        {v.score != null && (
                          <span className={sc(v.score)}>{Math.round(v.score)}/100</span>
                        )}
                      </div>
                      {v.score != null && <ProgressBar value={v.score} color={scBar(v.score)} />}
                      {v.comment && (
                        <p className="text-[11px] text-muted2 mt-1 leading-relaxed">{v.comment}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}

              <div className="card p-5">
                {analysis.strengths.length > 0 && (
                  <>
                    <h3 className="text-sm font-bold font-mono uppercase tracking-wider text-paper mb-3">strengths</h3>
                    <ul className="space-y-1.5 mb-4">
                      {analysis.strengths.map((s, i) => (
                        <li key={i} className="flex gap-2 text-sm">
                          <span className="text-ok shrink-0 mt-0.5">✓</span>
                          <span className="text-muted leading-snug">{s}</span>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                {analysis.improvements.length > 0 && (
                  <>
                    <h3 className="text-sm font-bold font-mono uppercase tracking-wider text-paper mb-3">improve</h3>
                    <ul className="space-y-1.5 mb-4">
                      {analysis.improvements.map((s, i) => (
                        <li key={i} className="flex gap-2 text-sm">
                          <span className="text-warn shrink-0 mt-0.5">→</span>
                          <span className="text-muted leading-snug">{s}</span>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                {analysis.roadmap.length > 0 && (
                  <>
                    <h3 className="text-sm font-bold font-mono uppercase tracking-wider text-paper mb-3">roadmap</h3>
                    <ol className="space-y-1.5">
                      {analysis.roadmap.map((r, i) => (
                        <li key={i} className="flex gap-2 text-sm">
                          <span className="text-cyan shrink-0 font-mono text-[10px] mt-0.5">
                            {String(i + 1).padStart(2, '0')}
                          </span>
                          <span className="text-muted leading-snug">{r}</span>
                        </li>
                      ))}
                    </ol>
                  </>
                )}
                {analysis.posture_score != null && (
                  <div className="mt-4 pt-3 border-t border-line">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted">Posture Score</span>
                      <span className={sc(analysis.posture_score)}>
                        {Math.round(analysis.posture_score)}/100
                      </span>
                    </div>
                    {analysis.posture_summary && (
                      <p className="text-[11px] text-muted2 mt-1">{analysis.posture_summary}</p>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Q&A breakdown — skipped questions show study card */}
            {analysis.qa_breakdown.length > 0 && (
              <>
                <h2 className="font-mono text-xl text-white mb-3">Answer Breakdown</h2>
                <div className="space-y-3">
                  {analysis.qa_breakdown.map((q: any, i: number) => {
                    if (q.skipped) {
                      return (
                        <SkippedTopicsCard
                          key={i}
                          question={q.question || `Question ${i + 1}`}
                          index={i}
                        />
                      )
                    }
                    return (
                      <div key={i} className="card p-5">
                        <div className="flex items-start justify-between gap-3 mb-3">
                          <span className="chip-gold shrink-0">Q{i + 1}</span>
                          <div className="flex items-center gap-2 shrink-0 flex-wrap justify-end">
                            {q.content_score != null && (
                              <span className={`text-sm font-semibold ${sc(q.content_score)}`}>
                                {Math.round(q.content_score)}/100
                              </span>
                            )}
                            {q.sentiment && (
                              <span className={`chip text-[9px] ${
                                q.sentiment === 'positive' ? 'chip-green' :
                                q.sentiment === 'negative' ? 'chip-red' : 'chip-amber'}`}>
                                {q.sentiment}
                              </span>
                            )}
                          </div>
                        </div>
                        <p className="text-sm font-semibold text-acid mb-2 leading-snug">{q.question}</p>
                        {q.answer && !isSkipped(q.answer) && (
                          <div className="pl-3 border-l-2 border-line mb-3">
                            <p className="text-xs text-muted leading-relaxed line-clamp-4">{q.answer}</p>
                          </div>
                        )}
                        {q.feedback && (
                          <div className="bg-acid/[0.06] border border-acid/20 rounded-none p-3 mb-2">
                            <p className="text-sm text-paper leading-relaxed">{q.feedback}</p>
                          </div>
                        )}
                        {q.keywords?.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mt-1">
                            {q.keywords.slice(0, 6).map((k: string) => (
                              <span key={k} className="chip bg-white/5 text-muted border-0 text-[10px]">{k}</span>
                            ))}
                          </div>
                        )}
                        <JudgeBars scores={q.judge_scores} overall={q.judge_overall} />
                      </div>
                    )
                  })}
                </div>
              </>
            )}

            {/* Fallback when no breakdown in analysis */}
            {analysis.qa_breakdown.length === 0 && questions.length > 0 && (
              <>
                <h2 className="font-mono text-xl text-white mb-3 mt-5">Session Questions</h2>
                <div className="space-y-3">
                  {questions.map((q, i) =>
                    isSkipped(q.answer_text)
                      ? <SkippedTopicsCard key={i} question={q.question_text ?? `Q${i + 1}`} index={i} />
                      : (
                        <div key={i} className="card p-5">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="chip-gold">Q{i + 1}</span>
                            {q.content_score != null && (
                              <span className={`text-sm font-semibold ${sc(q.content_score)}`}>
                                {Math.round(q.content_score)}/100
                              </span>
                            )}
                          </div>
                          <p className="text-sm font-semibold text-acid mb-2">{q.question_text}</p>
                          {q.answer_text && (
                            <p className="text-xs text-muted pl-3 border-l-2 border-line mb-2 leading-relaxed">
                              {q.answer_text}
                            </p>
                          )}
                          {q.ai_feedback && (
                            <div className="bg-acid/[0.06] border border-acid/20 rounded-none p-3">
                              <p className="text-sm text-paper">{q.ai_feedback}</p>
                            </div>
                          )}
                          <JudgeBars scores={q.judge_scores} overall={
                            q.judge_scores
                              ? Object.values(q.judge_scores).reduce((a, b) => a + (b ?? 0), 0) / 5
                              : undefined
                          } />
                        </div>
                      )
                  )}
                </div>
              </>
            )}

            <div className="flex gap-3 mt-6">
              <Link to="/practice" className="btn-primary no-underline">Practice Again →</Link>
              <Link to="/dashboard" className="btn-ghost no-underline">Dashboard</Link>
            </div>
          </>
        )}

        {/* ════════════════════════════════════════════════════════
            CASE C: Completed, has answers, no analysis yet, not generating
        ════════════════════════════════════════════════════════ */}
        {!noRealAnswers && !analysis && !analyzing && sess?.status === 'completed' && (
          <>
            <h2 className="font-mono text-xl text-white mb-3">Session Questions</h2>
            <div className="space-y-3 mb-6">
              {questions.map((q, i) =>
                isSkipped(q.answer_text)
                  ? <SkippedTopicsCard key={i} question={q.question_text ?? `Q${i + 1}`} index={i} />
                  : (
                    <div key={i} className="card p-5">
                      <span className="chip-gold mb-2 inline-flex">Q{i + 1}</span>
                      <p className="text-sm font-semibold text-acid mb-2">{q.question_text}</p>
                      {q.answer_text && (
                        <p className="text-xs text-muted pl-3 border-l-2 border-line leading-relaxed">
                          {q.answer_text}
                        </p>
                      )}
                    </div>
                  )
              )}
            </div>
            <button onClick={runAnalysis} disabled={analyzing} className="btn-primary">
              Generate Full Analysis
            </button>
          </>
        )}

        {/* Session still in progress */}
        {sess?.status !== 'completed' && !loading && (
          <div className="card p-8 text-center">
            <p className="text-lg text-white mb-2">Interview still in progress</p>
            <p className="text-sm text-muted mb-5">
              Complete or end the session to see your analysis here.
            </p>
            <Link to="/practice" className="btn-ghost no-underline">Go to Practice</Link>
          </div>
        )}

      </div>
    </div>
  )
}