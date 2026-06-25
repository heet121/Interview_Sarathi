from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Database ─────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./interview_sarathi.db"

    # ── JWT ──────────────────────────────────────────────────────
    SECRET_KEY: str = "your-super-secret-jwt-key-change-this-in-production-minimum-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7   # 7 days

    # ── LLM provider ─────────────────────────────────────────────
    # "auto"     → Claude if ANTHROPIC_API_KEY is set, else Gemini
    # "claude" / "gemini" → force a provider
    # "offline"  → no cloud LLM; dataset questions + DeBERTa judge only
    LLM_PROVIDER: str = "auto"

    # ── LLM — Anthropic Claude (Sonnet 4.6) ──────────────────────
    # Get a key at https://console.anthropic.com/ → Settings → API Keys
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    ANTHROPIC_BASE_URL: str = "https://api.anthropic.com/v1"
    ANTHROPIC_VERSION: str = "2023-06-01"
    # Adaptive-thinking effort: low | medium | high  (Sonnet 4.6 default is high)
    ANTHROPIC_EFFORT: str = "high"
    ANTHROPIC_MAX_TOKENS: int = 6000

    # ── LLM — Google Gemini (optional fallback provider) ─────────
    GEMINI_API_KEY: str = "your-gemini-api-key-here"
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"

    # ── Whisper STT ───────────────────────────────────────────────
    # "small" is notably more accurate than "base" and still runs fine on CPU.
    # Options (accuracy↑ / speed↓): tiny · base · small · medium · large-v3
    OPENAI_API_KEY: str = "your-openai-api-key-here"
    WHISPER_MODE: str = "local"
    WHISPER_LOCAL_MODEL: str = "small"

    # ── Storage ───────────────────────────────────────────────────
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_MB: int = 10
    DATASET_DIR: str = "dataset"

    # ── Answer scoring (DeBERTa judge + NLP) ─────────────────────
    JUDGE_ENABLED: bool = True
    JUDGE_MODEL_PATH: str = "models/judge/deberta-v3-base-v1"
    # judge = judge only | hybrid = judge + NLP blend | nlp = NLP only
    SCORING_MODE: str = "hybrid"
    # When False, skip LLM calls for per-answer feedback (judge still runs)
    LLM_FEEDBACK_ENABLED: bool = True

    # ── Email (password reset) ────────────────────────────────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@interviewsarathi.com"
    FRONTEND_URL: str = "http://localhost:3000"

    # ── Rate Limiting ─────────────────────────────────────────────
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_REGISTER: str = "3/minute"
    RATE_LIMIT_FORGOT_PASSWORD: str = "3/minute"

    # ── Google OAuth ──────────────────────────────────────────────
    # Get credentials at https://console.cloud.google.com/
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/oauth/google/callback"

    # ── GitHub OAuth ──────────────────────────────────────────────
    # Get credentials at https://github.com/settings/developers
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_REDIRECT_URI: str = "http://localhost:8000/api/auth/oauth/github/callback"

    # ── Admin Panel ───────────────────────────────────────────────
    # Set a strong secret — send as X-Admin-Key header to access /api/admin/*
    ADMIN_SECRET_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
