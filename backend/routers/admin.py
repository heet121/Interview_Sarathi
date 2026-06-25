from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.models import User, InterviewSession, SessionAnalysis, Resume, PostureLog
from config import settings
from dataset_service import _question_cache

router = APIRouter()


def _require_admin(x_admin_key: str = Header(..., alias="X-Admin-Key")):
    if not settings.ADMIN_SECRET_KEY:
        raise HTTPException(status_code=501, detail="Admin panel is not configured")
    if x_admin_key != settings.ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")


# ── Overview stats ────────────────────────────────────────────────
@router.get("/stats")
def get_stats(db: Session = Depends(get_db), _=Depends(_require_admin)):
    total_users    = db.query(func.count(User.id)).scalar()
    active_users   = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    total_sessions = db.query(func.count(InterviewSession.id)).scalar()
    completed      = db.query(func.count(InterviewSession.id)).filter(
                         InterviewSession.status == "completed").scalar()
    in_progress    = db.query(func.count(InterviewSession.id)).filter(
                         InterviewSession.status == "in_progress").scalar()

    avg_score = db.query(func.avg(InterviewSession.overall_score)).filter(
        InterviewSession.overall_score.isnot(None)
    ).scalar()

    total_resumes = db.query(func.count(Resume.id)).scalar()

    # Sessions in last 7 days
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    sessions_this_week = db.query(func.count(InterviewSession.id)).filter(
        InterviewSession.started_at >= week_ago
    ).scalar()

    # Top 5 companies practiced
    top_companies = (
        db.query(InterviewSession.company, func.count(InterviewSession.id).label("count"))
        .filter(InterviewSession.company.isnot(None))
        .group_by(InterviewSession.company)
        .order_by(func.count(InterviewSession.id).desc())
        .limit(5)
        .all()
    )

    # Score distribution
    score_bands = {"excellent": 0, "good": 0, "average": 0, "needs_work": 0}
    scores = db.query(InterviewSession.overall_score).filter(
        InterviewSession.overall_score.isnot(None)
    ).all()
    for (s,) in scores:
        if s >= 85:   score_bands["excellent"] += 1
        elif s >= 70: score_bands["good"]       += 1
        elif s >= 55: score_bands["average"]    += 1
        else:         score_bands["needs_work"] += 1

    return {
        "users": {
            "total":  total_users,
            "active": active_users,
        },
        "sessions": {
            "total":            total_sessions,
            "completed":        completed,
            "in_progress":      in_progress,
            "this_week":        sessions_this_week,
            "avg_score":        round(avg_score, 1) if avg_score else None,
            "score_bands":      score_bands,
        },
        "resumes_uploaded": total_resumes,
        "top_companies": [
            {"company": c, "sessions": n} for c, n in top_companies
        ],
        "dataset_cache": {
            "companies_cached": len(_question_cache),
            "total_questions":  sum(len(v) for v in _question_cache.values()),
        },
    }


# ── Users ─────────────────────────────────────────────────────────
@router.get("/users")
def list_users(
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(_require_admin),
):
    q = db.query(User)
    if search:
        q = q.filter(
            User.email.ilike(f"%{search}%") |
            User.full_name.ilike(f"%{search}%")
        )
    users = q.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    total = q.count()

    return {
        "total": total,
        "users": [
            {
                "id":              u.id,
                "email":           u.email,
                "full_name":       u.full_name,
                "college":         u.college,
                "is_active":       u.is_active,
                "created_at":      u.created_at,
                "sessions_count":  len(u.sessions),
                "resumes_count":   len(u.resumes),
            }
            for u in users
        ],
    }


@router.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db), _=Depends(_require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    sessions = (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == user_id)
        .order_by(InterviewSession.started_at.desc())
        .limit(10)
        .all()
    )
    return {
        "id":              user.id,
        "email":           user.email,
        "full_name":       user.full_name,
        "college":         user.college,
        "branch":          user.branch,
        "graduation_year": user.graduation_year,
        "cgpa":            user.cgpa,
        "is_active":       user.is_active,
        "created_at":      user.created_at,
        "resumes":         [{"id": r.id, "filename": r.filename, "skills": r.skills_extracted}
                            for r in user.resumes],
        "recent_sessions": [
            {
                "id":            s.id,
                "company":       s.company,
                "role":          s.role,
                "status":        s.status,
                "overall_score": s.overall_score,
                "started_at":    s.started_at,
            }
            for s in sessions
        ],
    }


@router.patch("/users/{user_id}")
def toggle_user(
    user_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    _=Depends(_require_admin),
):
    """Activate or deactivate a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = is_active
    db.commit()
    return {"message": f"User {'activated' if is_active else 'deactivated'}", "user_id": user_id}


# ── Sessions ──────────────────────────────────────────────────────
@router.get("/sessions")
def list_sessions(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(_require_admin),
):
    q = db.query(InterviewSession)
    if status:
        q = q.filter(InterviewSession.status == status)
    if company:
        q = q.filter(InterviewSession.company.ilike(f"%{company}%"))

    sessions = q.order_by(InterviewSession.started_at.desc()).offset(skip).limit(limit).all()
    total    = q.count()

    return {
        "total": total,
        "sessions": [
            {
                "id":            s.id,
                "user_id":       s.user_id,
                "user_email":    s.user.email if s.user else None,
                "company":       s.company,
                "role":          s.role,
                "interview_type":s.interview_type,
                "difficulty":    s.difficulty,
                "num_questions": s.num_questions,
                "status":        s.status,
                "overall_score": s.overall_score,
                "started_at":    s.started_at,
                "completed_at":  s.completed_at,
                "duration_sec":  s.duration_seconds,
            }
            for s in sessions
        ],
    }


@router.get("/sessions/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db), _=Depends(_require_admin)):
    s = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "id":            s.id,
        "user_id":       s.user_id,
        "user_email":    s.user.email if s.user else None,
        "company":       s.company,
        "role":          s.role,
        "status":        s.status,
        "overall_score": s.overall_score,
        "started_at":    s.started_at,
        "questions": [
            {
                "index":        q.question_index,
                "question":     q.question_text,
                "answer":       q.answer_text,
                "content_score":q.content_score,
                "ai_feedback":  q.ai_feedback,
                "keywords":     q.nlp_keywords,
            }
            for q in sorted(s.questions, key=lambda x: x.question_index or 0)
        ],
        "analysis": s.analysis.full_analysis_json if s.analysis else None,
    }


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db), _=Depends(_require_admin)):
    s = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(s)
    db.commit()
    return {"message": "Session deleted", "session_id": session_id}


# ── System health ─────────────────────────────────────────────────
@router.get("/health")
def admin_health(db: Session = Depends(get_db), _=Depends(_require_admin)):
    """Detailed system health — DB counts, cache status, config flags."""
    return {
        "database": {
            "users":          db.query(func.count(User.id)).scalar(),
            "sessions":       db.query(func.count(InterviewSession.id)).scalar(),
            "analyses":       db.query(func.count(SessionAnalysis.id)).scalar(),
            "resumes":        db.query(func.count(Resume.id)).scalar(),
            "posture_logs":   db.query(func.count(PostureLog.id)).scalar(),
        },
        "dataset_cache": {
            "companies": len(_question_cache),
            "questions": sum(len(v) for v in _question_cache.values()),
        },
        "config": {
            "smtp_configured":   bool(settings.SMTP_HOST),
            "google_oauth":      bool(settings.GOOGLE_CLIENT_ID),
            "github_oauth":      bool(settings.GITHUB_CLIENT_ID),
            "whisper_mode":      settings.WHISPER_MODE,
            "gemini_model":      settings.GEMINI_MODEL,
            "database_url":      settings.DATABASE_URL.split("///")[0],  # hide path
        },
    }
