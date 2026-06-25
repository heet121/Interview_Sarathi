from contextlib import asynccontextmanager
import asyncio
import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn

from database import engine, Base, SessionLocal
from config import settings
from routers import (
    auth, sessions, interview, analysis, posture,
    resume, admin, feedback_ws, dashboard, leaderboard, question_packs,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# Create all DB tables
Base.metadata.create_all(bind=engine)


def _ensure_sqlite_columns():
    """Add columns that create_all won't apply to existing SQLite tables."""
    if "sqlite" not in str(settings.DATABASE_URL).lower():
        return
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    if "session_questions" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("session_questions")}
    if "judge_scores" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE session_questions ADD COLUMN judge_scores JSON"))
        logger.info("Migrated session_questions.judge_scores column")


_ensure_sqlite_columns()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR,  exist_ok=True)
os.makedirs(settings.DATASET_DIR, exist_ok=True)


async def _startup_tasks():
    """Run on startup: load dataset cache + seed question bank + seed packs + warm NLP."""
    try:
        from dataset_service import load_all_questions
        from routers.question_packs import _seed_packs
        db = SessionLocal()
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: load_all_questions(db_session=db))
            await loop.run_in_executor(None, lambda: _seed_packs(db))
            logger.info("Startup tasks complete ✅")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Startup tasks failed (non-fatal): {e}")

    # Warm up heavy models in the background so the first request isn't slow.
    try:
        import nlp_service
        import posture_service
        import stt_service
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, nlp_service.warm_up)
        loop.run_in_executor(None, posture_service.warm_up)
        loop.run_in_executor(None, stt_service.warm_up)
        if settings.JUDGE_ENABLED:
            from ml import judge_service
            loop.run_in_executor(None, judge_service.warm_up)
        logger.info("Model warm-up (NLP + MediaPipe + Whisper + Judge) started in background…")
    except Exception as e:
        logger.warning(f"Model warm-up skipped: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(_startup_tasks())
    yield


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Interview Sarathi API",
    description="AI-powered mock interview platform — production v2.2",
    version="2.2.0",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("ENV", "dev") != "production" else None,
    redoc_url=None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:8000", "http://127.0.0.1:8000",
        settings.FRONTEND_URL,
        "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────
app.include_router(auth.router,            prefix="/api/auth",        tags=["Auth"])
app.include_router(resume.router,          prefix="/api/resume",      tags=["Resume"])
app.include_router(sessions.router,        prefix="/api/sessions",    tags=["Sessions"])
app.include_router(interview.router,       prefix="/api/interview",   tags=["Interview"])
app.include_router(analysis.router,        prefix="/api/analysis",    tags=["Analysis"])
app.include_router(posture.router,         prefix="/api/posture",     tags=["Posture"])
app.include_router(feedback_ws.router,     prefix="/api/feedback",    tags=["Live Feedback"])
app.include_router(dashboard.router,       prefix="/api/dashboard",   tags=["Dashboard"])
app.include_router(leaderboard.router,     prefix="/api/leaderboard", tags=["Leaderboard"])
app.include_router(question_packs.router,  prefix="/api/packs",       tags=["Question Packs"])
app.include_router(admin.router,           prefix="/api/admin",       tags=["Admin"])

# ── Frontend static files ─────────────────────────────────────────
_frontend = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(_frontend):
    app.mount("/static", StaticFiles(directory=_frontend), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(os.path.join(_frontend, "index.html"))

    @app.get("/{path:path}", include_in_schema=False)
    async def catch_all(path: str):
        target = os.path.join(_frontend, path)
        if os.path.isfile(target):
            return FileResponse(target)
        return FileResponse(os.path.join(_frontend, "index.html"))


@app.get("/health", tags=["Health"])
async def health():
    from dataset_service import _question_cache
    judge_status = "disabled"
    if settings.JUDGE_ENABLED:
        try:
            from ml.judge_service import _load, _resolve_path
            judge_status = "loaded" if _load() is not None else f"missing ({_resolve_path()})"
        except Exception as e:
            judge_status = f"error: {e}"
    return {
        "status":  "ok",
        "version": "2.2.0",
        "dataset": {
            "companies": len(_question_cache),
            "questions": sum(len(v) for v in _question_cache.values()),
        },
        "scoring": {
            "judge_enabled": settings.JUDGE_ENABLED,
            "judge_status": judge_status,
            "scoring_mode": settings.SCORING_MODE,
            "llm_provider": settings.LLM_PROVIDER,
            "llm_active": llm_enabled(),
        },
        "features": {
            "google_oauth":     bool(settings.GOOGLE_CLIENT_ID),
            "github_oauth":     bool(settings.GITHUB_CLIENT_ID),
            "email":            bool(settings.SMTP_HOST),
            "admin_panel":      bool(settings.ADMIN_SECRET_KEY),
            "leaderboard":      True,
            "gamification":     True,
            "question_packs":   True,
            "dashboard":        True,
        },
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
