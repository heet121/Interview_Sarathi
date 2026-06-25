// src/pages/LandingPage.tsx
import { Link } from 'react-router-dom'
import { FileText, Mic, Repeat, BarChart2, ArrowRight, Check, Minus, X } from 'lucide-react'
import Navbar from '@/components/layout/Navbar'

const PAIN_STATS = [
  { stat: '72%', accent: 'text-bad', bar: 'before:bg-bad',
    desc: 'of shortlisted students are rejected at interviews — not for lack of skills, but for poor communication and confidence.',
    src: 'NASSCOM Campus Hiring Report, 2023' },
  { stat: '1 in 3', accent: 'text-warn', bar: 'before:bg-warn',
    desc: 'students have never practiced speaking their answer out loud before a real interview. They freeze under pressure.',
    src: 'LinkedIn India Student Survey, 2024' },
  { stat: '₹5K+', accent: 'text-cyan', bar: 'before:bg-cyan',
    desc: 'is the average cost per session with a human interview coach. Most students cannot afford real practice.',
    src: 'Average coaching rates, India, 2024' },
]

const HOW_IT_WORKS = [
  { n: '01', Icon: FileText,  title: 'Tell it who you are',        desc: 'Upload your resume. Pick your target company, role, and difficulty. The AI reads your actual background and tailors every question.' },
  { n: '02', Icon: Mic,       title: 'Speak your answers',         desc: 'The interviewer speaks — you speak back. Voice is transcribed live. No typing. Just you, the AI, and a real conversation.' },
  { n: '03', Icon: Repeat,    title: 'Get challenged in real-time', desc: "Based on your exact words, the AI probes deeper or asks follow-ups. It's not a quiz. It reacts to you." },
  { n: '04', Icon: BarChart2, title: 'See where you failed',       desc: 'Every answer scored by our own model. Posture analysis. Communication weaknesses identified. A specific improvement plan generated.' },
]

const COMPARISON = [
  ['Listens to your actual voice',     'yes',    'peer',   'no'],
  ['Available 24/7, no scheduling',    'always', 'sched',  'yes'],
  ['Personalised to your resume',      'yes',    'no',     'no'],
  ['AI adapts in real-time',           'yes',    'peer',   'no'],
  ['Posture & communication feedback', 'live',   'no',     'no'],
  ['Deep AI report after each session','yes',    'peer',   'no'],
  ['Built for Indian placement drives','yes',    'no',     'partial'],
]

const TESTIMONIALS = [
  { text: 'The AI noticed I keep saying "basically" between every sentence. After 3 sessions I stopped completely. My Wipro interview felt totally different.',
    name: 'Anjali R.', role: 'CSE · VIT Vellore · placed at Wipro', init: 'A' },
  { text: "My answers were too long and I'd lose the interviewer halfway. The STAR feedback from the AI changed everything.",
    name: 'Rohan M.', role: 'IT · BITS Pilani · offer from Razorpay', init: 'R' },
  { text: 'The posture analysis was embarrassing — I look down constantly. No human mock interview had ever told me that.',
    name: 'Priya S.', role: 'ECE · NIT Warangal · cleared TCS Digital', init: 'P' },
]

const STATS = [
  { val: '10K+', lbl: 'students_coached', accent: 'text-acid' },
  { val: '94%',  lbl: 'satisfaction',     accent: 'text-ok' },
  { val: '50+',  lbl: 'target_companies', accent: 'text-cyan' },
  { val: '4.8',  lbl: 'avg_rating',       accent: 'text-warn' },
]

function Verdict({ v }: { v: string }) {
  if (v === 'no' || v === 'sched')
    return <span className="inline-flex items-center gap-1 text-bad/80"><X size={13} strokeWidth={3} />{v === 'sched' ? 'sched' : 'no'}</span>
  if (v === 'peer' || v === 'partial')
    return <span className="inline-flex items-center gap-1 text-warn"><Minus size={13} strokeWidth={3} />{v}</span>
  return <span className="inline-flex items-center gap-1 text-ok"><Check size={13} strokeWidth={3} />{v}</span>
}

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-bg">
      <Navbar />

      {/* ── HERO ─────────────────────────────────────── */}
      <section className="relative px-5 pt-16 pb-20 overflow-hidden grid-bg border-b-2 border-line">
        <div className="max-w-[1160px] mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12 items-center relative z-10">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 border-2 border-line bg-s1 mb-7">
              <span className="w-2 h-2 bg-acid blink" />
              <span className="font-mono text-[11px] font-bold text-acid tracking-wider uppercase">
                ./run mock-interview --ai
              </span>
            </div>

            <h1 className="text-[clamp(2.5rem,5.6vw,4.4rem)] text-paper mb-5">
              Practice interviews.<br />
              Stop getting{' '}
              <span className="marker-acid px-1.5 font-bold">rejected.</span>
            </h1>

            <p className="text-[15px] text-muted leading-relaxed max-w-[520px] mb-8">
              Most students walk into their first real interview having never practiced out loud.
              Interview Sarathi listens, adapts in real-time, and tells you{' '}
              <span className="text-paper font-medium">exactly where you went wrong</span>.
            </p>

            <div className="flex items-center gap-3 flex-wrap">
              <Link to="/practice" className="btn-primary no-underline">
                Start a Mock Interview <ArrowRight size={15} strokeWidth={2.5} />
              </Link>
              <Link to="/login" className="btn-ghost no-underline">
                Create Free Account
              </Link>
            </div>

            <p className="font-mono text-[11px] text-muted2 mt-6">
              <span className="text-acid">$</span> no_credit_card · chrome_&_edge · free_to_start
            </p>
          </div>

          {/* Terminal hero */}
          <div className="hidden lg:block">
            <div className="term shadow-[8px_8px_0_0_#0b0b0e]">
              <div className="term-bar">
                <span className="term-dot bg-bad" />
                <span className="term-dot bg-warn" />
                <span className="term-dot bg-ok" />
                <span className="ml-2">interview://session/google · SWE-II</span>
              </div>
              <div className="p-5 text-[12.5px] leading-relaxed space-y-2.5">
                <p><span className="text-violet">interviewer</span><span className="text-muted2"> » </span><span className="text-paper">Walk me through how you'd design a URL shortener.</span></p>
                <p><span className="text-cyan">you</span><span className="text-muted2"> » </span><span className="text-muted">"So I'd use a hash of the URL and store it in a database..."</span></p>
                <div className="border-2 border-line bg-[#15151b] p-3 my-1 space-y-1">
                  <p className="text-muted2">// model.judge(answer)</p>
                  <p><span className="text-acid">relevance</span>     <span className="text-paper">0.91</span>  <span className="text-ok">▰▰▰▰▰▰▰▰▰</span></p>
                  <p><span className="text-acid">correctness</span>   <span className="text-paper">0.74</span>  <span className="text-warn">▰▰▰▰▰▰▰</span></p>
                  <p><span className="text-acid">communication</span> <span className="text-paper">0.62</span>  <span className="text-warn">▰▰▰▰▰▰</span></p>
                </div>
                <p><span className="text-violet">interviewer</span><span className="text-muted2"> » </span><span className="text-paper">How would you handle hash collisions at scale?</span></p>
                <p className="text-muted2 flex items-center">
                  <span className="text-cyan">you</span><span className="text-muted2"> » </span>
                  <span className="inline-block w-2 h-4 bg-acid blink ml-0.5" />
                </p>
              </div>
            </div>

            <div className="grid grid-cols-4 gap-0 mt-0 border-2 border-t-0 border-line">
              {STATS.map((s, i) => (
                <div key={s.lbl} className={`p-3 text-center ${i > 0 ? 'border-l-2 border-line' : ''}`}>
                  <div className={`font-mono text-xl font-bold ${s.accent}`}>{s.val}</div>
                  <div className="font-mono text-[9px] text-muted2 truncate">{s.lbl}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── PAIN POINTS ──────────────────────────────── */}
      <section className="px-5 py-20 border-b-2 border-line">
        <div className="max-w-[1000px] mx-auto">
          <p className="nb-eyebrow mb-3">// the_problem</p>
          <h2 className="text-3xl md:text-4xl text-paper mb-10">
            Why most students struggle in placements
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {PAIN_STATS.map(p => (
              <div key={p.stat}
                className={`card p-6 relative pl-7 before:content-[''] before:absolute before:left-0 before:top-0
                  before:bottom-0 before:w-2 ${p.bar}`}>
                <div className={`font-mono text-4xl font-bold mb-3 ${p.accent}`}>{p.stat}</div>
                <p className="text-sm text-muted leading-relaxed mb-3">{p.desc}</p>
                <p className="font-mono text-[10px] text-muted2">› {p.src}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ─────────────────────────────── */}
      <section className="px-5 py-20 border-b-2 border-line">
        <div className="max-w-[1100px] mx-auto">
          <p className="nb-eyebrow mb-3">// how_it_works</p>
          <h2 className="text-3xl md:text-4xl text-paper mb-10">
            A real interview. <span className="text-muted2">Not a quiz.</span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 border-2 border-line">
            {HOW_IT_WORKS.map((h, i) => (
              <div key={h.n}
                className={`p-7 group hover:bg-acid transition-colors duration-100
                  ${i > 0 ? 'border-t-2 lg:border-t-0 lg:border-l-2 border-line' : ''}`}>
                <div className="flex items-center justify-between mb-5">
                  <span className="font-mono text-sm font-bold text-acid group-hover:text-ink">{h.n}</span>
                  <h.Icon size={20} className="text-muted group-hover:text-ink" strokeWidth={2} />
                </div>
                <p className="text-base font-bold text-paper group-hover:text-ink mb-2">{h.title}</p>
                <p className="text-[13px] text-muted group-hover:text-ink/80 leading-relaxed">{h.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── COMPARISON ───────────────────────────────── */}
      <section className="px-5 py-20 border-b-2 border-line">
        <div className="max-w-[920px] mx-auto">
          <p className="nb-eyebrow mb-3">// diff --compare</p>
          <h2 className="text-3xl md:text-4xl text-paper mb-10">
            Why not just use Pramp or LeetCode?
          </h2>
          <div className="border-2 border-line overflow-x-auto">
            <div className="grid grid-cols-[2fr_1fr_1fr_1fr] min-w-[600px] bg-[#15151b] border-b-2 border-line">
              {['feature', 'sarathi', 'pramp', 'leetcode'].map((h, i) => (
                <div key={h} className={`px-4 py-3.5 font-mono text-[11px] font-bold uppercase tracking-wider
                  ${i === 0 ? 'text-muted' : 'text-center'} ${i === 1 ? 'bg-acid text-ink' : 'text-paper'}`}>
                  {h}
                </div>
              ))}
            </div>
            {COMPARISON.map((row, ri) => (
              <div key={ri} className="grid grid-cols-[2fr_1fr_1fr_1fr] min-w-[600px] border-b-2 border-line
                last:border-b-0 hover:bg-white/[0.02] transition-colors">
                <div className="px-4 py-3 text-[13px] text-muted">{row[0]}</div>
                {[row[1], row[2], row[3]].map((v, vi) => (
                  <div key={vi} className={`px-4 py-3 font-mono text-[12px] text-center
                    ${vi === 0 ? 'bg-acid/[0.06] border-x-2 border-line' : ''}`}>
                    <Verdict v={v} />
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── TESTIMONIALS ─────────────────────────────── */}
      <section className="px-5 py-20 border-b-2 border-line">
        <div className="max-w-[1100px] mx-auto">
          <p className="nb-eyebrow mb-3">// stdout: real_students</p>
          <h2 className="text-3xl md:text-4xl text-paper mb-10">Before and after.</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {TESTIMONIALS.map(t => (
              <div key={t.name} className="card-hover p-6 flex flex-col gap-4">
                <div className="font-mono text-acid text-sm tracking-widest">★★★★★</div>
                <p className="text-[15px] text-paper leading-relaxed flex-1">"{t.text}"</p>
                <div className="flex items-center gap-3 pt-3 border-t-2 border-line">
                  <div className="w-9 h-9 bg-acid border-2 border-ink flex items-center justify-center
                    text-sm font-bold text-ink font-mono shrink-0">
                    {t.init}
                  </div>
                  <div className="min-w-0">
                    <p className="text-[13px] font-bold text-paper truncate">{t.name}</p>
                    <p className="font-mono text-[10px] text-muted2 truncate">{t.role}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────── */}
      <section className="px-5 py-20 border-b-2 border-line">
        <div className="max-w-[760px] mx-auto">
          <div className="bg-acid border-2 border-ink shadow-[8px_8px_0_0_#0b0b0e] p-10 md:p-14 text-center">
            <p className="font-mono text-[12px] font-bold text-ink/70 mb-4 uppercase tracking-wider">~/placement-drive $</p>
            <h2 className="text-3xl md:text-5xl text-ink mb-4">
              Closer than you think.
            </h2>
            <p className="text-[15px] text-ink/80 mb-8 max-w-md mx-auto leading-relaxed font-medium">
              Every day without practice is a day your competition is using it. It takes 15 minutes.
            </p>
            <div className="flex items-center justify-center gap-3 flex-wrap">
              <Link to="/practice"
                className="inline-flex items-center gap-2 px-6 py-3 text-[13px] font-bold uppercase tracking-wide
                  bg-ink text-acid border-2 border-ink no-underline shadow-[3px_3px_0_0_#f4f3ec]
                  hover:shadow-[5px_5px_0_0_#f4f3ec] hover:-translate-x-px hover:-translate-y-px
                  active:shadow-none active:translate-x-[3px] active:translate-y-[3px] transition-all duration-100">
                Start a Mock Interview <ArrowRight size={15} strokeWidth={2.5} />
              </Link>
              <Link to="/login"
                className="inline-flex items-center gap-2 px-6 py-3 text-[13px] font-bold uppercase tracking-wide
                  bg-transparent text-ink border-2 border-ink no-underline hover:bg-ink hover:text-acid transition-colors duration-100">
                Create Account
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ── FOOTER ───────────────────────────────────── */}
      <footer className="px-5 py-8">
        <div className="max-w-[1200px] mx-auto flex items-center justify-between flex-wrap gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <div className="w-6 h-6 bg-acid border-2 border-ink flex items-center justify-center">
                <span className="font-mono text-[11px] font-bold text-ink">IS</span>
              </div>
              <span className="font-mono text-sm font-bold text-paper">interview<span className="text-acid">_sarathi</span></span>
            </div>
            <p className="font-mono text-[11px] text-muted2">// AI interview coaching for every Indian student.</p>
          </div>
          <div className="flex gap-1 flex-wrap">
            {[{ to: '/practice', l: 'practice' }, { to: '/dashboard', l: 'dashboard' }, { to: '/leaderboard', l: 'leaderboard' }].map(l => (
              <Link key={l.to} to={l.to}
                className="font-mono text-[12px] text-muted hover:text-acid transition-colors no-underline px-2 py-1">
                {l.l}
              </Link>
            ))}
          </div>
        </div>
      </footer>
    </div>
  )
}
