"""
User Dashboard Router
GET /api/dashboard/me          — full personal analytics
GET /api/dashboard/progress    — score trend over time
GET /api/dashboard/companies   — performance breakdown by company
GET /api/dashboard/badges      — user badges + available badges
GET /api/dashboard/streaks     — streak info + calendar heatmap data
"""

from datetime import datetime, timezone, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.models import (
    User, InterviewSession, SessionAnalysis,
    UserBadge, BADGE_DEFINITIONS,
)
from utils.auth import get_current_user

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────

def _completed_sessions(user_id: int, db: Session):
    return (
        db.query(InterviewSession)
        .filter(
            InterviewSession.user_id == user_id,
            InterviewSession.status  == "completed",
            InterviewSession.overall_score.isnot(None),
        )
        .order_by(InterviewSession.completed_at.asc())
        .all()
    )


# ── Endpoints ─────────────────────────────────────────────────────

@router.get("/me")
def full_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Complete personal analytics dashboard in one call."""
    sessions = _completed_sessions(current_user.id, db)

    if not sessions:
        return {
            "user": {
                "full_name":      current_user.full_name,
                "email":          current_user.email,
                "total_points":   current_user.total_points or 0,
                "streak":         current_user.interview_streak or 0,
                "member_since":   current_user.created_at,
            },
            "summary": {"total_sessions": 0},
            "message": "No completed interviews yet. Start your first one!",
        }

    scores   = [s.overall_score for s in sessions]
    avg      = round(sum(scores) / len(scores), 1)
    best     = round(max(scores), 1)
    latest   = round(scores[-1], 1)
    trend    = round(scores[-1] - scores[-3], 1) if len(scores) >= 3 else 0

    # Scores by company
    by_company = defaultdict(list)
    for s in sessions:
        if s.company:
            by_company[s.company].append(s.overall_score)
    top_companies = sorted(
        [{"company": c, "avg_score": round(sum(v)/len(v), 1), "sessions": len(v)}
         for c, v in by_company.items()],
        key=lambda x: x["avg_score"], reverse=True,
    )[:5]

    # Score distribution
    bands = {"90-100": 0, "75-89": 0, "60-74": 0, "below-60": 0}
    for sc in scores:
        if sc >= 90:   bands["90-100"] += 1
        elif sc >= 75: bands["75-89"]  += 1
        elif sc >= 60: bands["60-74"]  += 1
        else:          bands["below-60"] += 1

    # Interview type breakdown
    type_counts = defaultdict(int)
    for s in sessions:
        type_counts[s.interview_type or "technical"] += 1

    # Time metrics
    total_minutes = sum((s.duration_seconds or 0) for s in sessions) // 60
    avg_duration  = total_minutes // len(sessions) if sessions else 0

    # Dimension averages from analyses
    dim_sums = defaultdict(list)
    for s in sessions:
        if s.analysis:
            a = s.analysis
            if a.content_score:       dim_sums["Content"].append(a.content_score)
            if a.communication_score: dim_sums["Communication"].append(a.communication_score)
            if a.confidence_score:    dim_sums["Confidence"].append(a.confidence_score)
            if a.relevance_score:     dim_sums["Relevance"].append(a.relevance_score)
            if a.star_score:          dim_sums["STAR"].append(a.star_score)
            if a.posture_score:       dim_sums["Posture"].append(a.posture_score)
    dimension_avgs = {
        k: round(sum(v)/len(v), 1) for k, v in dim_sums.items() if v
    }

    # Recent 5 sessions
    recent = [
        {
            "id":            s.id,
            "company":       s.company,
            "role":          s.role,
            "interview_type":s.interview_type,
            "difficulty":    s.difficulty,
            "score":         s.overall_score,
            "points_earned": s.points_earned or 0,
            "completed_at":  s.completed_at,
            "verdict":       s.analysis.verdict if s.analysis else None,
        }
        for s in reversed(sessions[-5:])
    ]

    # Badges
    user_badge_keys = {b.badge_key for b in current_user.badges}
    earned_badges = []
    for b in sorted(current_user.badges, key=lambda x: x.earned_at, reverse=True):
        k = b.badge_key
        if k in BADGE_DEFINITIONS:
            earned_badges.append({**BADGE_DEFINITIONS[k], "key": k, "earned_at": b.earned_at})

    return {
        "user": {
            "full_name":      current_user.full_name,
            "email":          current_user.email,
            "college":        current_user.college,
            "branch":         current_user.branch,
            "total_points":   current_user.total_points or 0,
            "streak":         current_user.interview_streak or 0,
            "member_since":   current_user.created_at,
        },
        "summary": {
            "total_sessions":       len(sessions),
            "avg_score":            avg,
            "best_score":           best,
            "latest_score":         latest,
            "score_trend":          trend,      # positive = improving
            "total_time_minutes":   total_minutes,
            "avg_duration_minutes": avg_duration,
            "companies_practiced":  len(by_company),
            "score_distribution":   bands,
            "interview_types":      dict(type_counts),
        },
        "dimension_averages":   dimension_avgs,
        "top_companies":        top_companies,
        "recent_sessions":      recent,
        "badges": {
            "earned":    earned_badges,
            "earned_count": len(earned_badges),
            "total_available": len(BADGE_DEFINITIONS),
        },
    }


@router.get("/progress")
def score_progress(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Score trend over the last N days — for a line chart."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    sessions = (
        db.query(InterviewSession)
        .filter(
            InterviewSession.user_id     == current_user.id,
            InterviewSession.status      == "completed",
            InterviewSession.completed_at >= since,
            InterviewSession.overall_score.isnot(None),
        )
        .order_by(InterviewSession.completed_at.asc())
        .all()
    )

    data_points = [
        {
            "date":    s.completed_at.strftime("%Y-%m-%d"),
            "score":   round(s.overall_score, 1),
            "company": s.company,
            "role":    s.role,
            "id":      s.id,
        }
        for s in sessions
    ]

    # 7-day rolling average
    rolling = []
    for i, p in enumerate(data_points):
        window = data_points[max(0, i-6): i+1]
        rolling.append(round(sum(x["score"] for x in window) / len(window), 1))

    return {
        "period_days":   days,
        "data_points":   data_points,
        "rolling_avg_7": rolling,
        "total_sessions": len(data_points),
    }


@router.get("/companies")
def company_breakdown(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Per-company performance breakdown."""
    sessions = _completed_sessions(current_user.id, db)
    by_company = defaultdict(list)
    for s in sessions:
        if s.company:
            by_company[s.company].append(s)

    result = []
    for company, slist in sorted(by_company.items(), key=lambda x: len(x[1]), reverse=True):
        scores = [s.overall_score for s in slist]
        result.append({
            "company":     company,
            "sessions":    len(slist),
            "avg_score":   round(sum(scores)/len(scores), 1),
            "best_score":  round(max(scores), 1),
            "latest_score":round(slist[-1].overall_score, 1),
            "improving":   (slist[-1].overall_score > slist[0].overall_score) if len(slist) > 1 else None,
            "roles":       list({s.role for s in slist if s.role}),
        })
    return {"companies": result}


@router.get("/badges")
def get_badges(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """All badges — earned and locked — with progress hints."""
    earned_keys = {b.badge_key: b.earned_at for b in current_user.badges}
    sessions    = _completed_sessions(current_user.id, db)
    total       = len(sessions)
    best_score  = max((s.overall_score for s in sessions), default=0)
    streak      = current_user.interview_streak or 0

    all_badges = []
    for key, info in BADGE_DEFINITIONS.items():
        earned = key in earned_keys
        hint   = _badge_progress_hint(key, total, best_score, streak, sessions)
        all_badges.append({
            "key":         key,
            "name":        info["name"],
            "emoji":       info["emoji"],
            "description": info["description"],
            "points":      info["points"],
            "earned":      earned,
            "earned_at":   earned_keys.get(key),
            "hint":        hint,
        })

    earned_list  = [b for b in all_badges if b["earned"]]
    locked_list  = [b for b in all_badges if not b["earned"]]
    return {
        "earned": earned_list,
        "locked": locked_list,
        "total_points_from_badges": sum(b["points"] for b in earned_list),
    }


def _badge_progress_hint(key, total, best_score, streak, sessions) -> str:
    hints = {
        "first_interview":  f"Complete your first interview ({total}/1)" if total < 1 else "",
        "streak_3":         f"Maintain a 3-day streak ({streak}/3)",
        "streak_7":         f"Maintain a 7-day streak ({streak}/7)",
        "streak_30":        f"Maintain a 30-day streak ({streak}/30)",
        "score_80":         f"Score 80+ in any interview (best: {round(best_score,1)})",
        "score_90":         f"Score 90+ in any interview (best: {round(best_score,1)})",
        "perfect_score":    f"Score 95+ in any interview (best: {round(best_score,1)})",
        "10_interviews":    f"Complete 10 interviews ({total}/10)",
        "25_interviews":    f"Complete 25 interviews ({total}/25)",
        "google_ready":     "Score 75+ in a Google interview",
        "amazon_ready":     "Score 75+ in an Amazon interview",
        "microsoft_ready":  "Score 75+ in a Microsoft interview",
        "all_rounder":      f"Practice 5 different companies ({len({s.company for s in sessions if s.company})}/5)",
        "speed_demon":      "Complete an interview in under 10 minutes",
    }
    return hints.get(key, "")


@router.get("/streaks")
def streak_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Streak info + 90-day activity heatmap for a GitHub-style calendar."""
    since = datetime.now(timezone.utc) - timedelta(days=90)
    sessions = (
        db.query(InterviewSession)
        .filter(
            InterviewSession.user_id     == current_user.id,
            InterviewSession.status      == "completed",
            InterviewSession.completed_at >= since,
        )
        .order_by(InterviewSession.completed_at.asc())
        .all()
    )

    # Build daily activity map
    daily = defaultdict(lambda: {"count": 0, "avg_score": 0, "scores": []})
    for s in sessions:
        if s.completed_at:
            day = s.completed_at.strftime("%Y-%m-%d")
            daily[day]["count"] += 1
            if s.overall_score:
                daily[day]["scores"].append(s.overall_score)

    heatmap = []
    today = datetime.now(timezone.utc).date()
    for i in range(90):
        d   = (today - timedelta(days=89-i)).isoformat()
        rec = daily.get(d, {"count": 0, "scores": []})
        heatmap.append({
            "date":      d,
            "count":     rec["count"],
            "avg_score": round(sum(rec["scores"])/len(rec["scores"]), 1) if rec["scores"] else 0,
        })

    return {
        "current_streak":   current_user.interview_streak or 0,
        "last_interview":   current_user.last_interview_date,
        "heatmap_90_days":  heatmap,
        "active_days":      sum(1 for d in heatmap if d["count"] > 0),
        "total_this_month": sum(1 for s in sessions
                                if s.completed_at and s.completed_at.month == today.month),
    }