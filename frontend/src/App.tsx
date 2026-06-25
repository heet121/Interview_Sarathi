// src/App.tsx
import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider } from '@/context/AuthContext'
import { ProtectedRoute, PageLoader } from '@/components/ui'

// Eagerly loaded (small, always needed)
import LoginPage          from '@/pages/LoginPage'
import OAuthCallbackPage  from '@/pages/OAuthCallbackPage'
import ForgotPasswordPage from '@/pages/ForgotPasswordPage'
import DashboardPage      from '@/pages/DashboardPage'

// Lazy-loaded (only on demand)
const LandingPage      = lazy(() => import('@/pages/LandingPage'))
const PracticePage     = lazy(() => import('@/pages/PracticePage'))
const InterviewPage    = lazy(() => import('@/pages/InterviewPage'))
const SessionPage      = lazy(() => import('@/pages/SessionPage'))
const ProfilePage      = lazy(() => import('@/pages/ProfilePage'))
const LeaderboardPage  = lazy(() => import('@/pages/LeaderboardPage'))

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: '#141419',
              border: '2px solid #2b2b35',
              color: '#ececf2',
              fontSize: '13px',
              fontFamily: '"JetBrains Mono", monospace',
              borderRadius: '0px',
              boxShadow: '4px 4px 0 0 #0b0b0e',
            },
            success: { iconTheme: { primary: '#a3e635', secondary: '#0b0b0e' } },
            error:   { iconTheme: { primary: '#f87171', secondary: '#0b0b0e' } },
            duration: 3500,
          }}
        />

        <Suspense fallback={<PageLoader />}>
          <Routes>
            {/* ── Public ─────────────────────────────────── */}
            <Route path="/"                element={<LandingPage />} />
            <Route path="/login"           element={<LoginPage />} />
            <Route path="/oauth-callback"  element={<OAuthCallbackPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />

            {/* ── Protected ──────────────────────────────── */}
            <Route path="/dashboard"    element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
            <Route path="/practice"     element={<ProtectedRoute><PracticePage /></ProtectedRoute>} />
            <Route path="/interview/:id" element={<ProtectedRoute><InterviewPage /></ProtectedRoute>} />
            <Route path="/sessions/:id" element={<ProtectedRoute><SessionPage /></ProtectedRoute>} />
            <Route path="/profile"      element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
            <Route path="/leaderboard"  element={<ProtectedRoute><LeaderboardPage /></ProtectedRoute>} />

            {/* ── Fallback ───────────────────────────────── */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  )
}
