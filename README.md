# Interview Sarathi — AI Mock Interview Coach

A full-stack web app that runs realistic mock interviews: it asks role/company-specific
questions, lets you answer by **voice or text**, scores each answer with real NLP models,
checks your **webcam posture & eye contact**, and produces a detailed feedback report.

---

## What's actually under the hood

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Interview questions & report** | Google Gemini 2.0 Flash | Free API. If the key is missing or rate-limited, the app **automatically falls back** to a real question dataset + heuristic report, so an interview never breaks. |
| **Answer relevance (NLP)** | `sentence-transformers` MiniLM (`all-MiniLM-L6-v2`) | Real semantic similarity between the question and your answer — detects off-topic answers. |
| **Sentiment (NLP)** | HuggingFace DistilBERT (`sst-2`) | Real transformer sentiment on each answer. |
| **Keywords** | Curated tech vocabulary + regex | Highlights technical terms you used. |
| **Speech → text** | Browser Web Speech API (live) + `faster-whisper` (fallback) | Live captions while you speak; Whisper transcribes uploaded audio for browsers without Web Speech. |
| **Posture & eye contact** | MediaPipe Pose + FaceMesh | Samples a webcam frame every ~6s, runs on CPU. (No DeepFace — it was removed because it was broken and slow.) |
| **Database** | SQLite + SQLAlchemy | Zero-config; file lives at `backend/interview_sarathi.db`. |
| **Auth** | JWT + bcrypt | Email/password, plus optional Google & GitHub OAuth. |
| **Frontend** | Vite + React + TypeScript + Tailwind | SPA on port 3000, proxies `/api` to the backend. |

> The heavy NLP models (MiniLM + DistilBERT) and MediaPipe are **lazy-loaded** and warmed
> up in the background at startup, so the server boots in ~2 seconds and the first answer
> isn't slow. Models download once (~360 MB) on first use and are cached afterward.

---

## Project structure

```
interview_sarathi_patched/
├── backend/                 # FastAPI app
│   ├── main.py              # App entry point + routers + static frontend mount
│   ├── config.py            # Settings loaded from .env
│   ├── database.py          # SQLAlchemy engine/session (SQLite)
│   ├── requirements.txt
│   ├── models/              # ORM models + Pydantic schemas
│   ├── routers/             # auth, sessions, interview, analysis, posture,
│   │                        #   resume, dashboard, leaderboard, question_packs, admin
│   ├── utils/auth.py        # JWT + bcrypt helpers
│   ├── llm_service.py       # Gemini calls + graceful fallbacks
│   ├── nlp_service.py       # MiniLM relevance + DistilBERT sentiment (+ fallback)
│   ├── stt_service.py       # Whisper speech-to-text
│   ├── posture_service.py   # MediaPipe posture analysis
│   ├── resume_service.py    # PDF/DOCX resume parsing + skill extraction
│   ├── dataset_service.py   # Company question dataset (cached)
│   ├── gamification_service.py
│   └── email_service.py
├── frontend/                # Vite + React + TS SPA
│   └── src/{pages,components,context,lib}
├── setup.ps1                # One-time setup (Windows)
└── run.ps1                  # Start backend + frontend (Windows)
```

---

## Quickstart (Windows / PowerShell)

**Prerequisites:** Python 3.10+, Node.js 18+.

```powershell
# 1. One-time setup (creates venv, installs Python + frontend deps)
.\setup.ps1

# 2. Add your free Gemini key to backend\.env
#    GEMINI_API_KEY=AIza...
#    Get one at https://aistudio.google.com/app/apikey  (no credit card)

# 3. Start both servers
.\run.ps1
```

Then open **http://localhost:3000**.

> The app still works **without** a valid Gemini key — it falls back to the bundled
> question dataset and a heuristic report. A real key just makes the questions and the
> final report richer.

### Manual start (any OS)

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

API docs: **http://localhost:8000/docs**

---

## Key API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register`, `/api/auth/login` | Account + JWT |
| POST | `/api/resume/upload` | Upload resume → extract skills |
| POST | `/api/sessions/` | Create an interview session |
| POST | `/api/interview/first-question` | Opening question (Gemini or dataset) |
| POST | `/api/interview/submit-answer` | Score answer (NLP) + next question |
| POST | `/api/interview/transcribe` | Whisper speech-to-text |
| POST | `/api/posture/analyze-frame` | MediaPipe posture on a webcam frame |
| POST | `/api/analysis/{session_id}` | Full feedback report |
| GET | `/api/dashboard/me` | Personal analytics |
| GET | `/api/leaderboard/all-time` | Leaderboard |
| GET | `/health` | Health check |

---

## Notes

- **Database** is SQLite — created automatically on first run, no setup needed.
- **OAuth / email password reset** are optional; leave the relevant `.env` values blank
  to disable them (the endpoints return a clean "not configured" response).
- **Admin API** (`/api/admin/*`) requires the `X-Admin-Key` header to match
  `ADMIN_SECRET_KEY` in `.env`; leave it blank to disable.
- **Secrets:** keep real API keys in `backend/.env` (git-ignored). Rotate any key that
  was ever committed.
