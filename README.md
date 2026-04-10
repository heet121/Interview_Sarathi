# 🎯 Interview Sarathi v2 — AI Interview Coach

Full-stack AI mock interview platform: real-time speech, posture & gesture analysis, and deep performance analytics.

---

## 🤖 Complete AI/ML Stack

| Layer | Technology | Type | Notes |
|-------|-----------|------|-------|
| **LLM** | Google Gemini 2.0 Flash | Transformer LLM | Free API, no credit card |
| **Speech-to-Text** | OpenAI Whisper (local) | DL / Transformer | Runs on CPU, no API key |
| **NLP** | spaCy `en_core_web_sm` | Statistical NLP | Keyword extraction, resume parsing |
| **Sentiment** | HuggingFace DistilBERT | Transformer DL | `distilbert-base-uncased-finetuned-sst-2-english` |
| **Posture (1)** | MediaPipe Pose + FaceMesh | CNN (Google TFLite) | Eye contact, head pose, shoulders |
| **Posture (2)** | DeepFace | CNN (VGG-Face) | Facial emotion detection |
| **Posture Combined** | MediaPipe 60% + DeepFace 40% | Combined CNN | Final posture score |
| **Database** | PostgreSQL + SQLAlchemy | — | 7 relational tables |
| **Auth** | JWT + bcrypt | — | Stateless token auth |

> **On CNN/DL models**: This project uses **pre-trained** CNN models via MediaPipe (Google's TFLite models) and DeepFace (VGG-Face). No custom model training is required — inference only. DistilBERT is a pre-trained Transformer DL model from HuggingFace.

---

## 🏗️ Project Structure

```
interview-sarathi/
├── backend/
│   ├── main.py                     # FastAPI app entry point
│   ├── database.py                 # PostgreSQL + SQLAlchemy
│   ├── config.py                   # Settings from .env
│   ├── requirements.txt
│   ├── .env.template               # Copy → .env, fill in keys
│   ├── models/
│   │   ├── models.py               # ORM: users, sessions, questions, posture_logs...
│   │   └── schemas.py              # Pydantic request/response schemas
│   ├── routers/
│   │   ├── auth.py                 # POST /register, /login, GET /me
│   │   ├── sessions.py             # CRUD for interview sessions
│   │   ├── interview.py            # Question gen, answer submit, STT
│   │   ├── analysis.py             # Gemini deep analysis
│   │   └── posture.py              # HTTP + WebSocket posture stream
│   ├── services/
│   │   ├── llm_service.py          # Google Gemini 2.0 Flash API
│   │   ├── nlp_service.py          # spaCy + DistilBERT sentiment
│   │   ├── stt_service.py          # Whisper local/API
│   │   └── posture_service.py      # MediaPipe + DeepFace combined
│   └── utils/
│       └── auth.py                 # JWT create/decode, bcrypt
├── frontend/
│   └── index.html                  # Full SPA (modified from v5)
│                                   # Changes: removed "View Sample" btn,
│                                   # removed footer copyright,
│                                   # full backend API integration injected
├── scripts/
│   ├── setup_db.sql                # PostgreSQL user + DB creation
│   └── load_dataset.py             # GitHub dataset → PostgreSQL
├── setup.sh                        # One-time setup
└── run.sh                          # Start server
```

---

## ⚡ Quickstart (localhost)

### Prerequisites
- Python 3.10+
- PostgreSQL 14+ (running)
- `ffmpeg` (for local Whisper)
- Google Gemini API key (free)

### Step 1 — PostgreSQL
```bash
sudo apt install postgresql          # Ubuntu/Debian
sudo systemctl start postgresql
psql -U postgres -f scripts/setup_db.sql
```

### Step 2 — Configure
```bash
cp backend/.env backend/.env
nano backend/.env   # Add GEMINI_API_KEY
```

Get your **free Gemini API key**: https://aistudio.google.com/app/apikey
- No credit card required
- 15 requests/minute free tier
- 1 million tokens/day

### Step 3 — Install ffmpeg (for Whisper)
```bash
sudo apt install ffmpeg          # Ubuntu/Debian
brew install ffmpeg              # macOS
```

### Step 4 — Setup & Run
```bash
chmod +x setup.sh run.sh
./setup.sh    # Install packages, download models, seed dataset
./run.sh      # Start server
```

Open **http://localhost:8000** — the frontend and API are served from the same port.

---

## 🌐 API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register` | ❌ | Create user account |
| POST | `/api/auth/login` | ❌ | Login → JWT token |
| GET | `/api/auth/me` | ✅ | Current user |
| POST | `/api/sessions/` | ✅ | Create interview session |
| GET | `/api/sessions/` | ✅ | List all sessions |
| GET | `/api/sessions/{id}` | ✅ | Session + Q&A + analysis |
| PATCH | `/api/sessions/{id}/complete` | ✅ | Mark session done |
| DELETE | `/api/sessions/{id}` | ✅ | Delete session |
| POST | `/api/interview/first-question` | ✅ | Gemini opening question |
| POST | `/api/interview/submit-answer` | ✅ | Answer → NLP → BERT → AI reply |
| POST | `/api/interview/transcribe` | ❌ | Whisper STT (base64 audio) |
| POST | `/api/interview/transcribe-file` | ✅ | Whisper STT (file upload) |
| POST | `/api/analysis/{session_id}` | ✅ | Run Gemini deep analysis |
| GET | `/api/analysis/{session_id}` | ✅ | Retrieve stored analysis |
| POST | `/api/posture/analyze-frame` | ✅ | Single frame analysis |
| WS | `/api/posture/ws/{session_id}` | ❌ | Real-time posture stream |
| GET | `/api/posture/status` | ❌ | Check MediaPipe/DeepFace status |
| GET | `/health` | ❌ | Health check |

Full interactive docs: **http://localhost:8000/docs**

---

## 🗄️ Database Schema (PostgreSQL)

```
users              → id, email, hashed_password, full_name, college, branch, cgpa
resumes            → id, user_id, filename, text_content, skills_extracted
interview_sessions → id, user_id, company, role, difficulty, num_questions, overall_score
session_questions  → id, session_id, question_text, answer_text, bert_label, bert_score, nlp_keywords
session_analyses   → id, session_id, overall_score, dimensions JSON, full_analysis_json
posture_logs       → id, session_id, timestamp_sec, mediapipe_label, deepface_emotion, posture_label
question_bank      → id, category, role, company, difficulty, question, answer_hint
```

---

## 🎥 Posture Analysis: How It Works

Every 6 seconds during the interview, the frontend captures a JPEG frame from the webcam and sends it over WebSocket to the backend.

**MediaPipe analysis (60% weight):**
- `FaceMesh`: detects if face is visible, estimates nose position for eye contact, measures eye level difference for head tilt
- `Pose`: detects left/right shoulder landmarks, checks for slouching (shoulder height difference > 6%), forward lean

**DeepFace analysis (40% weight):**
- Detects dominant facial emotion: happy / neutral / sad / fear / surprise / angry / disgust
- `happy`/`surprise` → +10% confidence boost
- `sad`/`fear`/`angry` → -12% confidence penalty
- Uses VGG-Face CNN model internally (downloaded on first use, ~100 MB)

**Combined score formula:**
```
posture_ratio * 35 + eye_ratio * 35 + face_ratio * 15 + happy_ratio * 10 + avg_confidence * 5
```

---

## 🧠 Sentiment Analysis: DistilBERT

- Model: `distilbert-base-uncased-finetuned-sst-2-english`
- Type: Transformer DL (fine-tuned on SST-2 sentiment dataset)
- Output: `POSITIVE` / `NEGATIVE` + confidence score (0.0–1.0)
- Used for: scoring each answer in the final report
- Lazy-loaded on first use (downloads ~270 MB model weights)

---

## 🔑 Getting Your Free Gemini API Key

1. Go to: https://aistudio.google.com/app/apikey
2. Sign in with Google account
3. Click **"Create API key"**
4. Copy the key → paste into `backend/.env` as `GEMINI_API_KEY=AIzaSy...`

**Free tier limits:** 15 requests/minute, 1M tokens/day — more than enough for localhost use.

---

## 🐛 Troubleshooting

**Backend won't start**
```bash
sudo systemctl status postgresql   # Check PostgreSQL is running
cat backend/.env                   # Verify DATABASE_URL
lsof -i :8000                      # Check port is free
```

**spaCy model missing**
```bash
source venv/bin/activate
python -m spacy download en_core_web_sm
```

**Whisper fails: "ffmpeg not found"**
```bash
sudo apt install ffmpeg   # Ubuntu
brew install ffmpeg        # macOS
```

**DeepFace slow on first run**
- It downloads ~100 MB VGG-Face model weights on first analysis. Subsequent runs are fast.

**BERT out of memory**
- DistilBERT needs ~500 MB RAM. Close other apps if needed.
- Model is lazy-loaded (only on first analysis request).

**Gemini API 429 rate limit**
- Free tier: 15 req/min. The interview flow uses ~1 req per answer, well within limits.
- If hit, wait 60s and retry.
