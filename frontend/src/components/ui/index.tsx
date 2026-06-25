// src/components/ui/index.tsx
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'

export function Spinner({ size = 6 }: { size?: number }) {
  return (
    <div
      className={`w-${size} h-${size} border-2 border-line border-t-acid`}
      style={{ animation: 'spin .7s linear infinite' }}
    />
  )
}

export function PageLoader() {
  return (
    <div className="min-h-screen bg-bg grid-bg flex flex-col items-center justify-center gap-3">
      <Spinner size={8} />
      <p className="font-mono text-xs text-muted2 blink">loading_modules…</p>
    </div>
  )
}

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <PageLoader />
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />
  return <>{children}</>
}

export function ScoreRing({ score, size = 80 }: { score: number; size?: number }) {
  const r   = (size / 2) - 6
  const c   = 2 * Math.PI * r
  const pct = Math.min(score, 100) / 100
  const color = score >= 80 ? '#4ade80' : score >= 60 ? '#fbbf24' : '#f87171'
  return (
    <svg width={size} height={size} className="rotate-[-90deg]">
      <circle cx={size/2} cy={size/2} r={r} stroke="#2b2b35"
        strokeWidth={5} fill="none" />
      <circle cx={size/2} cy={size/2} r={r} stroke={color}
        strokeWidth={5} fill="none" strokeDasharray={c}
        strokeDashoffset={c * (1 - pct)}
        style={{ transition: 'stroke-dashoffset 1s ease' }} />
      <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle"
        fill={color} fontSize={size * 0.22} fontWeight="700" fontFamily="JetBrains Mono, monospace"
        style={{ transform: 'rotate(90deg)', transformOrigin: 'center' }}>
        {Math.round(score)}
      </text>
    </svg>
  )
}

export function ScoreColor({ score }: { score: number }) {
  return score >= 80 ? 'text-ok' : score >= 60 ? 'text-warn' : 'text-bad'
}

export function ProgressBar({ value, color = '#a3e635' }: { value: number; color?: string }) {
  return (
    <div className="h-2 bg-s3 border border-line overflow-hidden">
      <div className="h-full transition-all duration-700"
        style={{ width: `${Math.min(value, 100)}%`, background: color }} />
    </div>
  )
}
