// src/pages/InterviewPage.tsx
import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import {
  Mic, MicOff, PhoneOff, Volume2, VolumeX,
  Send, SkipForward, Loader2, ChevronRight, RefreshCw,
  VideoOff,
} from 'lucide-react'
import clsx from 'clsx'
import toast from 'react-hot-toast'
import { sessionsApi, interviewApi, postureApi, resumeApi, errMsg } from '@/lib/api'
import {
  cameraLabel,
  isRemoteCameraLabel,
  listVideoInputsWithLabels,
  openWebcamStream,
  pickWebcamDevice,
} from '@/lib/camera'
import { Spinner } from '@/components/ui'

// ── Types ─────────────────────────────────────────────────────────────────────
interface LocationState {
  resumeText?: string
  config?: {
    company: string; role: string; interview_type: string
    difficulty: string; num_questions: number
  }
}

interface QA {
  index: number
  question: string
  answer: string
  skipped: boolean
}

// ── Waveform (AI speaking indicator) ─────────────────────────────────────────
function Waveform({ active }: { active: boolean }) {
  return (
    <div className="flex items-end gap-[3px] h-6">
      {Array.from({ length: 8 }).map((_, i) => (
        <div
          key={i}
          className={clsx(
            'w-[3px] rounded-full transition-all',
            active ? 'bg-teal animate-pulse-slow' : 'bg-muted2'
          )}
          style={{
            height: active
              ? `${5 + Math.sin(i * 0.9) * 8 + (i % 3) * 3}px`
              : '3px',
            animationDelay: `${i * 0.09}s`,
            animationDuration: `${0.5 + (i % 3) * 0.25}s`,
          }}
        />
      ))}
    </div>
  )
}

// ── Main InterviewPage ────────────────────────────────────────────────────────
export default function InterviewPage() {
  const { id }    = useParams<{ id: string }>()
  const navigate  = useNavigate()
  const location  = useLocation()
  const state     = (location.state || {}) as LocationState
  const sessionId = Number(id)

  const cfg          = state.config
  const [company,      setCompany]      = useState(cfg?.company || 'Interview')
  const [role,         setRole]         = useState(cfg?.role || 'Candidate')
  const [numQuestions, setNumQuestions] = useState(cfg?.num_questions || 5)

  // ── State ──────────────────────────────────────────────────────────
  const [currentQ,     setCurrentQ]     = useState('')
  const [currentIndex, setCurrentIndex] = useState(0)
  const [typedAnswer,  setTypedAnswer]  = useState('')
  const [spokenAnswer, setSpokenAnswer] = useState('')
  const [interimText,  setInterimText]  = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isEnding,     setIsEnding]     = useState(false)
  const [aiSpeaking,   setAiSpeaking]   = useState(false)
  const [muted,        setMuted]        = useState(false)
  const [listening,    setListening]    = useState(false)
  const [elapsed,      setElapsed]      = useState(0)
  const [loadingFirst, setLoadingFirst] = useState(true)
  const [loadError,    setLoadError]    = useState<string | null>(null)
  const [transcribing, setTranscribing] = useState(false)
  const [cameraError,  setCameraError]  = useState<string | null>(null)
  const [cameras,      setCameras]      = useState<MediaDeviceInfo[]>([])
  const [cameraId,     setCameraId]     = useState<string>('')
  const [qaLog,        setQaLog]        = useState<QA[]>([])
  const [posture,      setPosture]      = useState<{ label: string; eye: boolean; feedback: string } | null>(null)

  const videoRef         = useRef<HTMLVideoElement>(null)
  const canvasRef        = useRef<HTMLCanvasElement>(null)
  const textareaRef      = useRef<HTMLTextAreaElement>(null)
  const streamRef        = useRef<MediaStream | null>(null)
  const camPromiseRef    = useRef<Promise<MediaStream> | null>(null)  // dedupe getUserMedia (StrictMode)
  const transcriptEndRef = useRef<HTMLDivElement>(null)
  const startTime        = useRef(Date.now())
  const recognitionRef   = useRef<SpeechRecognition | null>(null)
  const shouldRestartRef = useRef(false)
  const endCalledRef     = useRef(false)
  const currentSpeechRef = useRef<string>('')

  // Mic / fallback transcription
  const audioStreamRef     = useRef<MediaStream | null>(null)
  const mediaRecorderRef   = useRef<MediaRecorder | null>(null)
  const audioChunksRef     = useRef<Blob[]>([])
  const fallbackNotifiedRef = useRef(false)  // showed the "live captions off" hint?
  const spokenAnswerRef    = useRef('')      // mirror of spokenAnswer for closures
  const turnBaselineRef    = useRef('')      // spokenAnswer before the current speak turn

  const lastTipRef       = useRef('')
  const lastPostureTipRef  = useRef('')

  // ── Fetch first question (recover session if router state was lost) ─
  const startInterview = useCallback(async () => {
    if (!sessionId || Number.isNaN(sessionId)) {
      navigate('/practice')
      return
    }
    setLoadError(null)
    setLoadingFirst(true)

    let resumeText = state.resumeText || ''
    try {
      const detail = await sessionsApi.get(sessionId)
      const s = detail.data.session
      if (s.status === 'completed') {
        navigate(`/sessions/${sessionId}`, { replace: true })
        return
      }
      setCompany(s.company || cfg?.company || 'Interview')
      setRole(s.role || cfg?.role || 'Candidate')
      setNumQuestions(s.num_questions || cfg?.num_questions || 5)

      if (!resumeText) {
        try {
          const latest = await resumeApi.latest()
          resumeText = latest.data?.text_content || ''
        } catch { /* resume optional */ }
      }

      const r = await interviewApi.firstQuestion({
        session_id: sessionId,
        resume_text: resumeText || undefined,
      })
      setCurrentQ(r.data.question)
      setLoadingFirst(false)
      setTimeout(() => {
        if (!muted && window.speechSynthesis) {
          const u = new SpeechSynthesisUtterance(r.data.question)
          u.rate = 0.92
          u.onstart = () => setAiSpeaking(true)
          u.onend = () => setAiSpeaking(false)
          window.speechSynthesis.speak(u)
        }
      }, 500)
    } catch (e) {
      const msg = errMsg(e) || 'Could not start the interview'
      setLoadError(msg)
      setLoadingFirst(false)
      toast.error(msg)
    }
  }, [sessionId, navigate, state.resumeText])

  useEffect(() => { startInterview() }, [startInterview])

  // ── Webcam ─────────────────────────────────────────────────────────
  const attachStream = useCallback(() => {
    const v = videoRef.current
    const s = streamRef.current
    if (v && s && v.srcObject !== s) {
      v.srcObject = s
      v.play?.().catch(() => {/* autoplay may need a tick; onLoadedMetadata retries */})
    }
  }, [])

  const setupCamera = useCallback(async (force = false, deviceId?: string) => {
    setCameraError(null)
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError('This page can’t access the camera. Open the app at http://localhost:3000 in Chrome or Edge.')
      return
    }
    try {
      const pickedId = deviceId ?? cameraId
      // Reuse a single in-flight request so React StrictMode's double-mount
      // (and rapid retries) never open the camera twice at once.
      if (force || !camPromiseRef.current) {
        camPromiseRef.current = (async () => {
          const inputs = await listVideoInputsWithLabels()
          setCameras(inputs)
          const resolvedId =
            (pickedId && inputs.some((d) => d.deviceId === pickedId) ? pickedId : undefined) ??
            pickWebcamDevice(inputs)?.deviceId ??
            ''
          if (resolvedId !== cameraId) setCameraId(resolvedId)
          return openWebcamStream(resolvedId || undefined)
        })()
      }
      const s = await camPromiseRef.current
      streamRef.current = s
      attachStream()
    } catch (err: any) {
      camPromiseRef.current = null   // allow Retry to re-request
      const name = err?.name
      if (name === 'NotAllowedError' || name === 'SecurityError')
        setCameraError('Camera access is blocked. Click the camera icon in the address bar, allow access, then press Retry.')
      else if (name === 'NotFoundError' || name === 'DevicesNotFoundError')
        setCameraError('No camera found. Connect a webcam and press Retry.')
      else if (name === 'NotReadableError' || name === 'TrackStartError' || name === 'AbortError')
        setCameraError('Your camera is busy in another app (Zoom, Teams, Meet…). Close it and press Retry.')
      else
        setCameraError('Could not start the camera. Press Retry, or continue with voice/text only.')
    }
  }, [attachStream, cameraId])

  const switchCamera = useCallback(async (nextId: string) => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    camPromiseRef.current = null
    setCameraId(nextId)
    await setupCamera(true, nextId)
  }, [setupCamera])

  useEffect(() => {
    if (loadingFirst) return
    setupCamera()
    return () => {
      streamRef.current?.getTracks().forEach(t => t.stop())
      streamRef.current = null
      camPromiseRef.current = null
    }
  }, [loadingFirst, setupCamera])

  // Re-attach when stream or video node is ready
  useEffect(() => {
    if (!loadingFirst) attachStream()
  }, [loadingFirst, attachStream])

  // ── Posture sampling ───────────────────────────────────────────────
  // Capture a webcam frame every 6s and send it to the backend (MediaPipe)
  // for posture + eye-contact analysis. Results are stored per session and
  // feed the "Posture & Presence" score in the final report.
  useEffect(() => {
    if (loadingFirst || !sessionId) return

    const captureAndSend = async () => {
      const video  = videoRef.current
      const canvas = canvasRef.current
      if (!video || !canvas || video.readyState < 2 || video.videoWidth === 0) return

      const w = 320
      const h = (video.videoHeight / video.videoWidth) * w || 240
      canvas.width = w
      canvas.height = h
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      ctx.drawImage(video, 0, 0, w, h)
      const frame = canvas.toDataURL('image/jpeg', 0.6).split(',')[1]

      try {
        const res = await postureApi.analyzeFrame({
          session_id:    sessionId,
          frame_base64:  frame,
          timestamp_sec: Math.floor((Date.now() - startTime.current) / 1000),
        })
        setPosture({
          label:    res.data.posture_label,
          eye:      res.data.eye_contact,
          feedback: res.data.feedback || '',
        })
      } catch { /* posture is best-effort — never block the interview */ }
    }

    const t = setInterval(captureAndSend, 6000)
    const warm = setTimeout(captureAndSend, 2500)
    return () => { clearInterval(t); clearTimeout(warm) }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadingFirst, sessionId])

  // ── Timer ──────────────────────────────────────────────────────────
  useEffect(() => {
    const t = setInterval(
      () => setElapsed(Math.floor((Date.now() - startTime.current) / 1000)),
      1000
    )
    return () => clearInterval(t)
  }, [])

  // ── Auto-scroll live transcript ────────────────────────────────────
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [interimText, spokenAnswer])

  // Mirror spokenAnswer into a ref so async (Whisper) callbacks read the latest.
  useEffect(() => { spokenAnswerRef.current = spokenAnswer }, [spokenAnswer])

  // ── Live coaching tips (WebSocket → toast popups, no fixed panel) ──
  useEffect(() => {
    if (loadingFirst || !sessionId) return
    const token = localStorage.getItem('token')
    if (!token) return

    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${proto}//${window.location.host}/api/feedback/ws/${sessionId}?token=${encodeURIComponent(token)}`
    let ws: WebSocket
    try {
      ws = new WebSocket(wsUrl)
    } catch {
      return
    }

    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data)
        const tip: string = data.tip || ''
        if (!tip || tip === 'Start speaking...' || tip === lastTipRef.current) return
        lastTipRef.current = tip
        toast(tip, { id: 'live-coach-tip', duration: 5500 })
      } catch { /* ignore */ }
    }

    const push = () => {
      const text = `${spokenAnswer} ${interimText}`.trim()
      if (ws.readyState === WebSocket.OPEN && text.length > 8) {
        ws.send(JSON.stringify({ text, question: currentQ }))
      }
    }
    const iv = setInterval(push, 2500)
    return () => { clearInterval(iv); ws.close() }
  }, [loadingFirst, sessionId, spokenAnswer, interimText, currentQ])

  // Posture coaching as popup when camera detects issues
  useEffect(() => {
    if (loadingFirst || !posture?.feedback) return
    if (posture.label === 'good' && posture.eye) return
    const msg = posture.feedback
    if (msg && msg !== lastPostureTipRef.current) {
      lastPostureTipRef.current = msg
      toast(msg, { id: 'posture-tip', duration: 4500 })
    }
  }, [posture, loadingFirst])

  // ── TTS ────────────────────────────────────────────────────────────
  const speakText = useCallback((text: string) => {
  if (!text) return
  if (muted || !window.speechSynthesis) return
  currentSpeechRef.current = text
  window.speechSynthesis.cancel()
  const u = new SpeechSynthesisUtterance(text)
  u.rate    = 0.92
  u.onstart = () => setAiSpeaking(true)
  u.onend   = () => { setAiSpeaking(false); currentSpeechRef.current = '' }
  u.onerror = () => { setAiSpeaking(false); currentSpeechRef.current = '' }
  window.speechSynthesis.speak(u)
}, [muted])
  // ── Re-route audio when headphones are plugged/unplugged ───────────
useEffect(() => {
  const handleDeviceChange = () => {
    if (currentSpeechRef.current && !muted) {
      const text = currentSpeechRef.current
      window.speechSynthesis.cancel()
      setTimeout(() => {
        const u = new SpeechSynthesisUtterance(text)
        u.rate    = 0.92
        u.onstart = () => setAiSpeaking(true)
        u.onend   = () => { setAiSpeaking(false); currentSpeechRef.current = '' }
        u.onerror = () => { setAiSpeaking(false); currentSpeechRef.current = '' }
        window.speechSynthesis.speak(u)
      }, 300)
    }
  }
  navigator.mediaDevices.addEventListener('devicechange', handleDeviceChange)
  return () => navigator.mediaDevices.removeEventListener('devicechange', handleDeviceChange)
}, [muted])

  // ── Speech recognition (live captions, primary) ────────────────────
  const buildRecognition = useCallback((): SpeechRecognition | null => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SR) return null
    const r: SpeechRecognition = new SR()
    r.continuous     = true
    r.interimResults = true
    r.lang           = 'en-IN'

    r.onresult = (e: SpeechRecognitionEvent) => {
      let interim = ''
      let final   = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript
        if (e.results[i].isFinal) final += t
        else interim += t
      }
      setInterimText(interim)
      if (final) {
        setInterimText('')
        setSpokenAnswer(prev => prev ? `${prev} ${final.trim()}` : final.trim())
      }
    }

    // Web Speech often fails ("network" on flaky links, "not-allowed", etc).
    // We never show a scary error: the audio is recorded in parallel and
    // transcribed by the backend (Whisper) when the mic is stopped.
    r.onerror = (e: SpeechRecognitionErrorEvent) => {
      if (['network', 'not-allowed', 'service-not-allowed', 'audio-capture'].includes(e.error)) {
        shouldRestartRef.current = false   // stop retrying live; rely on Whisper
        if (!fallbackNotifiedRef.current) {
          fallbackNotifiedRef.current = true
          toast('Live captions unavailable here — keep speaking, your answer is transcribed when you press Stop.',
            { icon: 'ℹ️', duration: 5000 })
        }
      }
    }

    r.onend = () => {
      if (shouldRestartRef.current) {
        setTimeout(() => {
          if (shouldRestartRef.current) {
            try { recognitionRef.current?.start() } catch {}
          }
        }, 200)
      }
    }
    return r
  }, [])

  // ── Audio recording → Whisper fallback ─────────────────────────────
  const startRecording = (stream: MediaStream) => {
    audioChunksRef.current = []
    let mime = ''
    if (typeof MediaRecorder !== 'undefined') {
      if (MediaRecorder.isTypeSupported?.('audio/webm')) mime = 'audio/webm'
      else if (MediaRecorder.isTypeSupported?.('audio/mp4')) mime = 'audio/mp4'
    }
    try {
      const mr = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream)
      mr.ondataavailable = ev => { if (ev.data && ev.data.size) audioChunksRef.current.push(ev.data) }
      mr.start()
      mediaRecorderRef.current = mr
    } catch {
      mediaRecorderRef.current = null
    }
  }

  const stopMicStream = () => {
    audioStreamRef.current?.getTracks().forEach(t => t.stop())
    audioStreamRef.current = null
  }

  // Whisper is the authoritative transcript: it replaces the live Web-Speech
  // text for the current speak-turn with a more accurate transcription.
  const transcribeRecording = async () => {
    const chunks = audioChunksRef.current
    audioChunksRef.current = []
    stopMicStream()
    if (!chunks.length) return
    const type = chunks[0].type || 'audio/webm'
    const blob = new Blob(chunks, { type })
    if (blob.size < 1600) return   // essentially silence

    setTranscribing(true)
    try {
      const ext  = type.includes('mp4') ? 'mp4' : 'webm'
      const file = new File([blob], `answer.${ext}`, { type })
      const res  = await interviewApi.transcribeFile(file)
      const text = (res.data.transcript || '').trim()
      if (text && !text.startsWith('[Transcription unavailable')) {
        const base = turnBaselineRef.current.trim()
        setSpokenAnswer(base ? `${base} ${text}` : text)
      } else if (!spokenAnswerRef.current.trim()) {
        toast('No speech detected — try again or type your answer.', { icon: '🎤' })
      }
      // else: transcription empty but Web Speech already captured something — keep it.
    } catch {
      // Keep whatever Web Speech captured live; don't lose the answer.
      toast('Used live captions (server transcription unavailable).', { icon: 'ℹ️' })
    } finally {
      setTranscribing(false)
    }
  }

  useEffect(() => {
    return () => {
      shouldRestartRef.current = false
      try { recognitionRef.current?.abort() } catch {}
      try { mediaRecorderRef.current?.stop() } catch {}
      stopMicStream()
    }
  }, [])

  const startListening = async () => {
    if (isSubmitting || isEnding || listening || transcribing) return

    // Grab the mic ourselves — clear permission prompt + clean audio for
    // accurate Whisper transcription (noise suppression, mono, gain control).
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl:  true,
          channelCount:     1,
        },
      })
    } catch (err: any) {
      const name = err?.name
      if (name === 'NotAllowedError' || name === 'SecurityError')
        toast.error('Microphone is blocked. Click the lock icon in the address bar, allow the mic, then try again.')
      else if (name === 'NotFoundError' || name === 'DevicesNotFoundError')
        toast.error('No microphone found. Plug one in, or type your answer instead.')
      else
        toast.error('Could not access the microphone. You can type your answer instead.')
      return
    }

    audioStreamRef.current      = stream
    turnBaselineRef.current     = spokenAnswerRef.current   // text before this turn
    fallbackNotifiedRef.current = false
    startRecording(stream)

    // Best-effort live captions (Whisper produces the final accurate text on Stop).
    recognitionRef.current = buildRecognition()
    if (recognitionRef.current) {
      shouldRestartRef.current = true
      try { recognitionRef.current.start() } catch {}
    }

    setListening(true)
  }

  const stopListening = () => {
    shouldRestartRef.current = false
    try { recognitionRef.current?.stop() } catch {}
    setListening(false)
    setInterimText('')

    const mr = mediaRecorderRef.current
    mediaRecorderRef.current = null
    if (mr && mr.state !== 'inactive') {
      // Always run Whisper for an accurate final transcript.
      mr.onstop = () => transcribeRecording()
      try { mr.stop() } catch { stopMicStream() }
    } else {
      stopMicStream()
    }
  }

  // ── Helpers ────────────────────────────────────────────────────────
  const fmt = (s: number) =>
    `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

  const progress    = Math.round((currentIndex / numQuestions) * 100)
  const finalAnswer = typedAnswer.trim() || spokenAnswer.trim()
  const wordCount   = finalAnswer.split(/\s+/).filter(Boolean).length

  // ── End interview ──────────────────────────────────────────────────
  const endInterview = useCallback(async (log: QA[]) => {
    if (endCalledRef.current) return
    endCalledRef.current = true
    setIsEnding(true)
    try { await sessionsApi.complete(sessionId, Math.floor((Date.now() - startTime.current) / 1000)) } catch {}
    navigate(`/sessions/${sessionId}`, { replace: true })
  }, [sessionId, navigate])

  // ── Submit answer ──────────────────────────────────────────────────
  const submitAnswer = async (skip = false) => {
    if (isSubmitting || isEnding) return
    if (!skip && transcribing) {
      toast('Still transcribing your voice — one moment…', { icon: '⏳' })
      return
    }
    const answer = skip ? '[Skipped]' : finalAnswer
    if (!skip && !answer) { toast.error('Please type or speak your answer first.'); return }

    setIsSubmitting(true)
    stopListening()

    try {
      const res = await interviewApi.submitAnswer({
        session_id:     sessionId,
        question_index: currentIndex,
        question_text:  currentQ,
        answer_text:    answer,
        skipped:        skip,
      })

      const newLog: QA[] = [
        ...qaLog,
        { index: currentIndex, question: currentQ, answer, skipped: skip },
      ]
      setQaLog(newLog)
      setTypedAnswer('')
      setSpokenAnswer('')
      setInterimText('')

      if (!skip && res.data.keywords?.length)
        toast(`Key terms: ${res.data.keywords.slice(0, 3).join(', ')}`, { icon: '💡', duration: 3000 })

      if (!skip && res.data.judge_overall != null) {
        const js = res.data.judge_scores
        const dims = js
          ? `R:${Math.round(js.relevance ?? 0)} C:${Math.round(js.correctness ?? 0)} D:${Math.round(js.depth ?? 0)}`
          : ''
        toast(
          `Judge: ${Math.round(res.data.judge_overall)}/100${dims ? ` · ${dims}` : ''}`,
          { icon: '⚖️', duration: 4500 },
        )
      }
      if (!skip && res.data.quick_feedback)
        toast(res.data.quick_feedback, { icon: '📝', duration: 4000 })

      const rd      = res.data
      const isLast  = rd.is_last ?? false
      const nextIdx = rd.question_index ?? (currentIndex + 1)
      const aiReply = rd.ai_reply ?? ''

      setCurrentQ(aiReply)
      setCurrentIndex(nextIdx)
      speakText(aiReply)

      if (isLast) await endInterview(newLog)
    } catch (e) {
      toast.error(errMsg(e) || 'Failed to submit. Try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleEndEarly = () => {
    if (window.confirm('End the interview now? Your progress will be saved.'))
      endInterview(qaLog)
  }

  // ── Loading / error screen ─────────────────────────────────────────
  if (loadingFirst) {
    return (
      <div className="h-screen bg-bg flex flex-col items-center justify-center gap-4">
        <Spinner size={8} />
        <p className="text-sm text-muted animate-pulse font-mono">Setting up your interview room…</p>
      </div>
    )
  }

  if (loadError) {
    return (
      <div className="h-screen bg-bg flex flex-col items-center justify-center gap-4 px-6 text-center">
        <p className="text-bad font-mono text-sm max-w-md">{loadError}</p>
        <p className="text-muted text-xs max-w-sm">Make sure the backend is running on port 8000, then retry.</p>
        <button onClick={startInterview} className="btn-primary">Retry interview setup</button>
        <button onClick={() => navigate('/practice')} className="btn-ghost">Back to setup</button>
      </div>
    )
  }

  // ── Main 4-panel UI ────────────────────────────────────────────────
  return (
    <div
      className="flex flex-col h-screen bg-bg text-white overflow-hidden"
      style={{ fontFamily: 'Geist, sans-serif' }}
    >

      {/* ── Top bar ──────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-line bg-s1 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-teal animate-pulse" />
          <span className="text-sm font-medium text-white">{company}</span>
          <ChevronRight size={12} className="text-muted2" />
          <span className="text-sm text-muted">{role}</span>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-28 h-1.5 rounded-full bg-s3 overflow-hidden">
              <div
                className="h-full bg-teal rounded-full transition-all duration-700"
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="text-xs text-muted tabular-nums">{currentIndex}/{numQuestions}</span>
          </div>

          <span className="text-xs font-mono text-muted2 tabular-nums">{fmt(elapsed)}</span>

          <button
            onClick={() => {
              setMuted(m => !m)
              window.speechSynthesis?.cancel()
              setAiSpeaking(false)
            }}
            className="p-1.5 rounded-md hover:bg-s3 text-muted hover:text-white transition-colors"
            title={muted ? 'Unmute AI voice' : 'Mute AI voice'}
          >
            {muted ? <VolumeX size={16} /> : <Volume2 size={16} />}
          </button>

          <button
            onClick={handleEndEarly}
            disabled={isEnding}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-red-900/40
              hover:bg-red-800/60 text-red-400 hover:text-red-300 text-xs font-medium
              transition-colors disabled:opacity-50"
          >
            {isEnding ? <Loader2 size={13} className="animate-spin" /> : <PhoneOff size={13} />}
            End
          </button>
        </div>
      </div>

      {/* ── 4-panel body ─────────────────────────────────────── */}
      <div className="flex flex-1 gap-3 p-3 min-h-0 overflow-hidden">

        {/* ════ LEFT COLUMN ══════════════════════════════════════════ */}
        <div className="flex flex-col gap-3 min-h-0" style={{ width: '48%' }}>

          {/* Panel 1 — Question ───────────────────────────────────── */}
          <div
            className="flex flex-col rounded-none bg-s2 border-2 border-line overflow-hidden"
            style={{ flex: '1.4 1 0' }}
          >
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-line shrink-0">
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded-full bg-teal/15 flex items-center justify-center">
                  <span className="text-[10px] font-bold text-teal">Q</span>
                </div>
                <span className="text-xs font-medium text-muted uppercase tracking-wider">
                  Question {currentIndex + 1} of {numQuestions}
                </span>
              </div>
              {aiSpeaking && (
                <span className="flex items-center gap-1 text-[10px] text-teal font-mono">
                  <span className="w-1.5 h-1.5 rounded-full bg-teal animate-pulse inline-block" />
                  Speaking…
                </span>
              )}
            </div>

            {/* Full question text — scrollable */}
            <div className="flex-1 overflow-y-auto px-5 py-4">
              {currentQ
                ? (
                  <p
                    className="text-base text-white leading-[1.7] font-light"
                    style={{ fontFamily: 'Instrument Serif, Georgia, serif' }}
                  >
                    {currentQ}
                  </p>
                )
                : (
                  <div className="h-full flex items-center justify-center">
                    <Spinner size={5} />
                  </div>
                )
              }
            </div>

            {/* Waveform + Repeat btn always at bottom */}
            <div className="px-4 py-3 border-t border-line shrink-0 flex items-center justify-between">
              <Waveform active={aiSpeaking} />
              <button
                onClick={() => speakText(currentQ)}
                disabled={!currentQ || aiSpeaking || muted}
                title={muted ? 'Unmute AI voice to use this' : 'Repeat question aloud'}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                  bg-s3 hover:bg-border text-muted hover:text-white border-2 border-line
                  transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <Volume2 size={12} />
                Repeat Question
              </button>
            </div>
          </div>

          {/* Panel 2 — Live speech transcript ─────────────────────── */}
          <div
            className="flex flex-col rounded-none bg-s2 border-2 border-line overflow-hidden"
            style={{ flex: '1 1 0' }}
          >
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-line shrink-0">
              <div className="flex items-center gap-2">
                <Mic size={13} className={listening ? 'text-red-400' : 'text-muted2'} />
                <span className="text-xs font-medium text-muted uppercase tracking-wider">Live Speech</span>
                {listening && (
                  <span className="flex items-center gap-1 text-[10px] text-red-400 font-mono">
                    <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse inline-block" />
                    REC
                  </span>
                )}
                {transcribing && (
                  <span className="flex items-center gap-1 text-[10px] text-teal font-mono">
                    <Loader2 size={10} className="animate-spin" />
                    Transcribing…
                  </span>
                )}
              </div>
              <button
                onClick={listening ? stopListening : startListening}
                disabled={isSubmitting || isEnding || transcribing}
                className={clsx(
                  'px-3 py-1 rounded-lg text-xs font-medium transition-all border disabled:opacity-50',
                  listening
                    ? 'bg-red-600/20 text-red-400 hover:bg-red-600/30 border-red-600/40'
                    : 'bg-teal/10 text-teal hover:bg-teal/20 border-teal/30'
                )}
              >
                {listening
                  ? <><MicOff size={11} className="inline mr-1" />Stop</>
                  : transcribing
                    ? <><Loader2 size={11} className="inline mr-1 animate-spin" />Working…</>
                    : <><Mic size={11} className="inline mr-1" />Speak</>}
              </button>
            </div>

            {/* Every word shown as you speak */}
            <div className="flex-1 overflow-y-auto px-4 py-3">
              {transcribing && !spokenAnswer && !interimText
                ? (
                  <div className="h-full flex flex-col items-center justify-center gap-2 text-center">
                    <Loader2 size={18} className="text-teal animate-spin" />
                    <p className="text-muted text-[11px] max-w-[180px] leading-relaxed">
                      Transcribing your answer…
                    </p>
                  </div>
                )
                : !spokenAnswer && !interimText
                ? (
                  <div className="h-full flex flex-col items-center justify-center gap-2 text-center">
                    <div className="w-8 h-8 rounded-full bg-s3 flex items-center justify-center">
                      <Mic size={14} className="text-muted2" />
                    </div>
                    <p className="text-muted text-[11px] max-w-[180px] leading-relaxed">
                      Press <strong className="text-muted">Speak</strong> and talk. Your words appear live, or are transcribed when you press Stop.
                    </p>
                  </div>
                )
                : (
                  <>
                    {spokenAnswer && (
                      <p className="text-white text-sm leading-relaxed">{spokenAnswer}</p>
                    )}
                    {interimText && (
                      <p className="text-muted text-sm italic mt-1">
                        {interimText}
                        <span className="not-italic text-teal font-bold ml-0.5">|</span>
                      </p>
                    )}
                    <div ref={transcriptEndRef} />
                  </>
                )
              }
            </div>

            <div className="px-4 py-2 border-t border-line shrink-0 flex items-center justify-between">
              <span className="text-[10px] text-muted2 font-mono">
                {(spokenAnswer + ' ' + interimText).trim().split(/\s+/).filter(Boolean).length} words spoken
              </span>
              {(spokenAnswer || interimText) && (
                <button
                  onClick={() => { setSpokenAnswer(''); setInterimText('') }}
                  className="text-[11px] text-muted2 hover:text-muted transition-colors"
                >
                  Clear
                </button>
              )}
            </div>
          </div>

        </div>{/* end LEFT COLUMN */}

        {/* ════ RIGHT COLUMN ═════════════════════════════════════════ */}
        <div className="flex flex-col gap-3 flex-1 min-h-0">

          {/* Panel 3 — User webcam (black background) ──────────────── */}
          <div
            className="relative rounded-none overflow-hidden border-2 border-line"
            style={{ flex: '1 1 0', background: '#000000' }}
          >
            <div className="absolute inset-0 bg-black" />

            <video
              ref={videoRef}
              autoPlay
              muted
              playsInline
              onLoadedMetadata={() => videoRef.current?.play().catch(() => {})}
              className="absolute inset-0 w-full h-full object-cover scale-x-[-1]"
            />
            <canvas ref={canvasRef} className="hidden" />

            {cameraError && (
              <div className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-3
                bg-black/85 px-6 text-center">
                <div className="w-12 h-12 rounded-full bg-red-900/40 flex items-center justify-center">
                  <VideoOff size={22} className="text-red-400" />
                </div>
                <p className="text-[13px] text-white/80 max-w-[320px] leading-relaxed">{cameraError}</p>
                <button
                  onClick={() => setupCamera(true)}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold
                    bg-teal text-bg hover:bg-teal/90 transition-all"
                >
                  <RefreshCw size={13} /> Retry camera
                </button>
              </div>
            )}

            {posture && (
              <div className="absolute top-3 left-1/2 -translate-x-1/2 z-10 flex items-center gap-2
                bg-black/65 backdrop-blur rounded-full px-3 py-1.5">
                <div className={clsx(
                  'w-2 h-2 rounded-full',
                  posture.label === 'good' && posture.eye ? 'bg-green-400' : 'bg-yellow-400'
                )} />
                <span className="text-[11px] font-medium text-white">
                  {posture.label === 'good' && posture.eye
                    ? 'Good posture & eye contact'
                    : posture.feedback || 'Adjust your posture'}
                </span>
              </div>
            )}

            {listening && (
              <div className="absolute top-3 left-3 z-10 flex items-center gap-2
                bg-red-600/80 backdrop-blur rounded-full px-3 py-1.5">
                <div className="w-2 h-2 rounded-full bg-white animate-pulse" />
                <span className="text-xs font-medium">Recording</span>
              </div>
            )}

            <div className="absolute top-3 right-3 z-10 flex flex-col items-end gap-2">
              <span className="bg-black/60 backdrop-blur rounded-md px-2.5 py-1 text-xs text-muted font-mono">
                YOU
              </span>
              {cameras.length > 1 && (
                <select
                  value={cameraId}
                  onChange={(e) => switchCamera(e.target.value)}
                  className="max-w-[220px] truncate rounded-md border border-white/20 bg-black/70 px-2 py-1 text-[10px] text-white"
                  title="Choose camera"
                >
                  {cameras.map((cam, i) => (
                    <option key={cam.deviceId} value={cam.deviceId}>
                      {isRemoteCameraLabel(cam.label) ? '📱 ' : '💻 '}
                      {cameraLabel(cam, i)}
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div className="absolute bottom-0 left-0 right-0 z-10 px-3 py-2
              bg-gradient-to-t from-black/80 to-transparent">
              <p className="text-[10px] text-white/50 font-mono">
                Posture &amp; eye contact analysed · Sit straight and look at the camera
              </p>
            </div>
          </div>

          {/* Panel 4 — Type answer (full width) ───────────────────── */}
          <div
            className="flex flex-col rounded-none border-2 border-line overflow-hidden bg-s2"
            style={{ flex: '1 1 0' }}
          >
            <div className="flex flex-col flex-1 min-w-0">
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-line shrink-0">
                <span className="text-xs font-medium text-muted uppercase tracking-wider">
                  Type Your Answer
                </span>
                <span className="text-[10px] text-muted2 font-mono">{wordCount} words</span>
              </div>

              <textarea
                ref={textareaRef}
                value={typedAnswer}
                onChange={e => setTypedAnswer(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault()
                    submitAnswer(false)
                  }
                }}
                placeholder={
                  spokenAnswer
                    ? 'Voice answer captured — add extra notes here…'
                    : 'Type your answer, or use the mic on the left…'
                }
                disabled={isSubmitting || isEnding}
                className="flex-1 resize-none bg-transparent px-4 py-3 text-sm text-white
                  placeholder-muted2 outline-none leading-relaxed"
              />

              <div className="flex items-center gap-2 px-4 py-2.5 border-t border-line shrink-0">
                <span className="text-[10px] text-muted2 mr-auto opacity-60 hidden sm:block">
                  Ctrl+Enter to send
                </span>
                <button
                  onClick={() => submitAnswer(true)}
                  disabled={isSubmitting || isEnding}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium
                    bg-s3 hover:bg-border text-muted hover:text-white border-2 border-line
                    transition-all disabled:opacity-40"
                >
                  <SkipForward size={13} /> Skip
                </button>

                <button
                  onClick={() => submitAnswer(false)}
                  disabled={isSubmitting || isEnding || transcribing || (!typedAnswer.trim() && !spokenAnswer.trim())}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold
                    bg-teal text-bg hover:bg-teal/90 transition-all
                    disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {isSubmitting
                    ? <><Loader2 size={14} className="animate-spin" /> Sending…</>
                    : transcribing
                      ? <><Loader2 size={14} className="animate-spin" /> Transcribing…</>
                      : <><Send size={13} /> Send</>}
                </button>
              </div>
            </div>
          </div>

        </div>{/* end RIGHT COLUMN */}
      </div>
    </div>
  )
}