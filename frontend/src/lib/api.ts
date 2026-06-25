// src/lib/api.ts
import axios, { AxiosError } from 'axios'

const BASE = import.meta.env.VITE_API_URL || ''   // empty = use Vite proxy

// OAuth redirects must go directly to the backend (not through Vite proxy)
// because window.location.href navigations bypass the Vite dev proxy
const BACKEND_DIRECT = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: BASE,
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT to every request
api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

// 401 → clear storage and redirect to login
api.interceptors.response.use(
  r => r,
  (err: AxiosError) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ── Helper to extract error message from FastAPI ──────────────────
export const errMsg = (e: unknown): string => {
  const err = e as AxiosError<{ detail?: string | {msg:string}[] }>
  const d = err.response?.data?.detail
  if (!d) return 'Something went wrong'
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map(x => x.msg).join(', ')
  return 'Something went wrong'
}

// ── Auth ──────────────────────────────────────────────────────────
export const authApi = {
  register: (body: RegisterBody) => api.post<TokenResp>('/api/auth/register', body),
  login:    (body: LoginBody)    => api.post<TokenResp>('/api/auth/login', body),
  me:       ()                   => api.get<UserOut>('/api/auth/me'),
  updateMe: (body: Partial<UserOut>) => api.patch<UserOut>('/api/auth/me', body),
  forgotPassword: (email: string) => api.post('/api/auth/forgot-password', { email }),
  resetPassword:  (token: string, new_password: string) =>
    api.post('/api/auth/reset-password', { token, new_password }),
  changePassword: (current_password: string, new_password: string) =>
    api.post('/api/auth/change-password', { current_password, new_password }),
  // Pass current SPA origin so OAuth returns to the same host (3000 vs 8000 vs 127.0.0.1)
  googleUrl: () => {
    const origin = encodeURIComponent(typeof window !== 'undefined' ? window.location.origin : '')
    return `${BACKEND_DIRECT}/api/auth/oauth/google?frontend=${origin}`
  },
  githubUrl: () => {
    const origin = encodeURIComponent(typeof window !== 'undefined' ? window.location.origin : '')
    return `${BACKEND_DIRECT}/api/auth/oauth/github?frontend=${origin}`
  },
}

// ── Resume ────────────────────────────────────────────────────────
export const resumeApi = {
  upload: (file: File) => {
    const fd = new FormData(); fd.append('file', file)
    return api.post<ResumeOut>('/api/resume/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  list:    ()   => api.get<ResumeOut[]>('/api/resume/'),
  latest:  ()   => api.get<LatestResumeResp>('/api/resume/latest'),
  get:     (id: number) => api.get<LatestResumeResp>(`/api/resume/${id}`),
  delete:  (id: number) => api.delete(`/api/resume/${id}`),
}

// ── Sessions ──────────────────────────────────────────────────────
export const sessionsApi = {
  create:   (body: SessionCreate)  => api.post<SessionOut>('/api/sessions/', body),
  list:     (skip=0, limit=50)     => api.get<SessionOut[]>(`/api/sessions/?skip=${skip}&limit=${limit}`),
  get:      (id: number)           => api.get<SessionDetail>(`/api/sessions/${id}`),
  complete: (id: number, duration_seconds=0) =>
    api.patch(`/api/sessions/${id}/complete`, null, { params: { duration_seconds } }),
  delete:   (id: number)           => api.delete(`/api/sessions/${id}`),
}

// ── Interview ─────────────────────────────────────────────────────
export const interviewApi = {
  companies:    ()                      => api.get<{ companies: string[] }>('/api/interview/companies'),
  firstQuestion:(body: FirstQBody)      => api.post<QuestionResp>('/api/interview/first-question', body),
  submitAnswer: (body: SubmitBody)      => api.post<AnswerFeedback>('/api/interview/submit-answer', body),
  transcribeFile:(file: File)           => {
    const fd = new FormData(); fd.append('file', file)
    return api.post<{ transcript: string }>('/api/interview/transcribe-file', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

// ── Analysis ──────────────────────────────────────────────────────
export const analysisApi = {
  generate: (sessionId: number) => api.post<AnalysisResult>(`/api/analysis/${sessionId}`),
  get:      (sessionId: number) => api.get<AnalysisResult>(`/api/analysis/${sessionId}`),
}

// ── Posture ───────────────────────────────────────────────────────
export const postureApi = {
  status: () => api.get('/api/posture/status'),
  analyzeFrame: (body: { session_id: number; frame_base64: string; timestamp_sec: number }) =>
    api.post<PostureResult>('/api/posture/analyze-frame', body),
}

// ── Dashboard ─────────────────────────────────────────────────────
export const dashboardApi = {
  me:        () => api.get<DashboardData>('/api/dashboard/me'),
  progress:  (days=30) => api.get<ProgressData>(`/api/dashboard/progress?days=${days}`),
  companies: () => api.get<{ companies: CompanyStats[] }>('/api/dashboard/companies'),
  badges:    () => api.get<BadgesData>('/api/dashboard/badges'),
  streaks:   () => api.get<StreakData>('/api/dashboard/streaks'),
}

// ── Leaderboard ───────────────────────────────────────────────────
export const leaderboardApi = {
  weekly:    () => api.get<LeaderboardResp>('/api/leaderboard/weekly'),
  monthly:   () => api.get<LeaderboardResp>('/api/leaderboard/monthly'),
  allTime:   () => api.get<LeaderboardResp>('/api/leaderboard/all-time'),
  myRanks:   () => api.get('/api/leaderboard/me'),
  company:   (company: string) => api.get<LeaderboardResp>(`/api/leaderboard/company?company=${encodeURIComponent(company)}`),
  college:   () => api.get<LeaderboardResp>('/api/leaderboard/college'),
}

// ── Types matching backend schemas exactly ─────────────────────────
export interface RegisterBody {
  email: string; password: string; full_name?: string
  college?: string; branch?: string; graduation_year?: string; cgpa?: string
}
export interface LoginBody { email: string; password: string }
export interface UserOut {
  id: number; email: string; full_name?: string; college?: string
  branch?: string; graduation_year?: string; cgpa?: string; is_active: boolean
}
export interface TokenResp { access_token: string; token_type: string; user: UserOut }
export interface ResumeOut { id: number; filename?: string; skills_extracted?: string[]; created_at?: string }
export interface LatestResumeResp {
  id: number; filename: string; text_content: string; skills_extracted: string[]; created_at: string
}
export interface SessionCreate {
  company?: string; role?: string; interview_type?: string
  difficulty?: string; num_questions?: number; skills_focus?: string; custom_focus?: string
}
export interface SessionOut {
  id: number; user_id: number; company?: string; role?: string
  interview_type?: string; difficulty?: string; num_questions?: number
  status: string; overall_score?: number; started_at?: string
}
export interface SessionQuestion {
  question_index: number; question_text?: string; answer_text?: string
  bert_label?: string; bert_score?: number; content_score?: number
  communication_score?: number; relevance_score?: number
  judge_scores?: Record<string, number>; judge_overall?: number
  ai_feedback?: string; keywords?: string[]
}
export interface JudgeScores {
  relevance?: number; correctness?: number; depth?: number
  communication?: number; structure?: number
}
export interface SessionDetail {
  session: SessionOut; questions: SessionQuestion[]; analysis?: AnalysisResult | null
}
export interface FirstQBody { session_id: number; resume_text?: string }
export interface QuestionResp { question: string; question_index: number; is_last: boolean; source?: string }
export interface SubmitBody {
  session_id: number; question_index: number; question_text: string; answer_text: string
  skipped?: boolean
}
export interface AnswerFeedback {
  ai_reply: string; bert_label?: string; bert_score?: number
  keywords?: string[]; quick_feedback?: string; llm_score?: number; llm_feedback?: string
  content_score?: number; communication_score?: number; relevance_score?: number
  judge_overall?: number; judge_scores?: JudgeScores; scoring_engine?: string
  question_index?: number; is_last?: boolean
}
export interface PostureResult {
  posture_label: string; eye_contact: boolean; confidence_level: number; emotion?: string; feedback?: string
}
export interface AnalysisResult {
  overall_score: number; verdict: string; overall_summary: string
  strengths: string[]; improvements: string[]
  dimensions: Record<string, { score?: number; comment?: string }>
  qa_breakdown: {
    question: string; answer: string; feedback: string
    content_score: number; communication_score: number; relevance_score?: number
    judge_scores?: JudgeScores; judge_overall?: number; scoring_engine?: string
    sentiment?: string; keywords?: string[]; skipped?: boolean
  }[]
  roadmap: string[]; posture_score?: number; posture_summary?: string
  gamification?: { points_earned?: number; badges_earned?: { name: string; emoji: string }[] }
}
export interface DashboardData {
  user: { full_name?: string; email: string; college?: string; branch?: string; total_points: number; streak: number; member_since: string }
  summary: {
    total_sessions: number; avg_score: number; best_score: number; latest_score: number
    score_trend: number; total_time_minutes: number; companies_practiced: number
    score_distribution: Record<string,number>; interview_types: Record<string,number>
  }
  dimension_averages: Record<string,number>
  top_companies: { company: string; avg_score: number; sessions: number }[]
  recent_sessions: { id:number; company:string; role:string; interview_type:string; difficulty:string; score:number; points_earned:number; completed_at:string; verdict?:string }[]
  badges: { earned: BadgeItem[]; earned_count: number; total_available: number }
}
export interface ProgressData {
  data_points: { date:string; score:number; company:string; role:string; id:number }[]
  rolling_avg_7: number[]; total_sessions: number; period_days: number
}
export interface CompanyStats { company:string; sessions:number; avg_score:number; best_score:number; latest_score:number; improving:boolean|null; roles:string[] }
export interface BadgeItem { key:string; name:string; emoji:string; description:string; points:number; earned:boolean; earned_at?:string; hint?:string }
export interface BadgesData { earned: BadgeItem[]; locked: BadgeItem[]; total_points_from_badges: number }
export interface StreakData { current_streak:number; last_interview?:string; heatmap_90_days:{date:string;count:number;avg_score:number}[]; active_days:number; total_this_month:number }
export interface LeaderboardEntry { rank:number; user_id:number; full_name:string; college?:string; avatar_initial:string; avg_score:number; sessions_count:number; points:number; streak:number; badges_count:number; is_me:boolean }
export interface LeaderboardResp { leaderboard: LeaderboardEntry[]; my_entry?:LeaderboardEntry; total_players:number }
