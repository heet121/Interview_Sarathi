import logging
from datetime import datetime, timezone, date, timedelta
from typing import List, Tuple

from sqlalchemy.orm import Session
from models.models import User, InterviewSession, UserBadge, LeaderboardEntry, BADGE_DEFINITIONS

logger = logging.getLogger(__name__)


# ── Points Formula ────────────────────────────────────────────────

def _calculate_points(score: float, difficulty: str, duration_sec: int, num_questions: int) -> int:

    base        = int(score)                           # 0-100
    diff_mult   = {"easy": 1.0, "medium": 1.5, "hard": 2.0}.get(difficulty or "medium", 1.5)
    speed_bonus = 20 if 0 < duration_sec < 600 else 0  # under 10 min
    full_bonus  = 15 if num_questions >= 5 else 0      # completed all questions
    return int(base * diff_mult) + speed_bonus + full_bonus


# ── Streak ────────────────────────────────────────────────────────

def _update_streak(user: User, db: Session) -> int:
    """Increment streak if user interviewed today or yesterday, else reset."""
    today = date.today()
    last  = user.last_interview_date
    last_date = last.date() if last else None

    if last_date == today:
        pass                                           # already counted today
    elif last_date == today - timedelta(days=1):
        user.interview_streak = (user.interview_streak or 0) + 1
    else:
        user.interview_streak = 1                      # streak broken — restart

    user.last_interview_date = datetime.now(timezone.utc)
    return user.interview_streak


# ── Badge Checker ─────────────────────────────────────────────────

def _award_badge(user: User, badge_key: str, db: Session) -> bool:
    """Award a badge if the user doesn't already have it. Returns True if newly awarded."""
    existing = db.query(UserBadge).filter(
        UserBadge.user_id == user.id,
        UserBadge.badge_key == badge_key,
    ).first()
    if existing:
        return False
    db.add(UserBadge(user_id=user.id, badge_key=badge_key))
    bonus = BADGE_DEFINITIONS.get(badge_key, {}).get("points", 0)
    user.total_points = (user.total_points or 0) + bonus
    logger.info(f"Badge awarded: user={user.id} badge={badge_key} +{bonus}pts")
    return True


def _check_badges(
    user: User,
    session: InterviewSession,
    total_completed: int,
    streak: int,
    score: float,
    db: Session,
) -> List[str]:
    """Check all badge conditions and return list of newly awarded badge keys."""
    new_badges = []

    def award(key):
        if _award_badge(user, key, db):
            new_badges.append(key)

    # Milestone badges
    if total_completed >= 1:  award("first_interview")
    if total_completed >= 10: award("10_interviews")
    if total_completed >= 25: award("25_interviews")

    # Streak badges
    if streak >= 3:  award("streak_3")
    if streak >= 7:  award("streak_7")
    if streak >= 30: award("streak_30")

    # Score badges
    if score >= 80: award("score_80")
    if score >= 90: award("score_90")
    if score >= 95: award("perfect_score")

    # Company-specific badges
    company = (session.company or "").lower()
    if score >= 75:
        if "google"    in company: award("google_ready")
        if "amazon"    in company: award("amazon_ready")
        if "microsoft" in company: award("microsoft_ready")

    # Speed badge
    if 0 < (session.duration_seconds or 0) < 600:
        award("speed_demon")

    # All-rounder — practiced 5 different companies
    from sqlalchemy import func
    distinct_companies = db.query(
        func.count(func.distinct(InterviewSession.company))
    ).filter(
        InterviewSession.user_id == user.id,
        InterviewSession.status == "completed",
        InterviewSession.company.isnot(None),
    ).scalar() or 0
    if distinct_companies >= 5:
        award("all_rounder")

    return new_badges


# ── Leaderboard Refresh ───────────────────────────────────────────

def _get_period_keys() -> Tuple[str, str]:
    """Return ISO week key and month key for today."""
    today = date.today()
    week_key  = today.strftime("%G-W%V")   # e.g. "2024-W42"
    month_key = today.strftime("%Y-%m")    # e.g. "2024-10"
    return week_key, month_key


def _upsert_leaderboard(user: User, session: InterviewSession, db: Session):
    """Update weekly, monthly, and all-time leaderboard entries."""
    score    = session.overall_score or 0
    points   = user.total_points or 0
    periods  = list(_get_period_keys()) + ["all_time"]

    for period in periods:
        entry = db.query(LeaderboardEntry).filter(
            LeaderboardEntry.user_id == user.id,
            LeaderboardEntry.period  == period,
        ).first()

        if entry:
            entry.score_sum      = (entry.score_sum or 0) + score
            entry.sessions_count = (entry.sessions_count or 0) + 1
            entry.avg_score      = entry.score_sum / entry.sessions_count
            entry.points         = points
        else:
            db.add(LeaderboardEntry(
                user_id=user.id,
                period=period,
                score_sum=score,
                sessions_count=1,
                avg_score=score,
                points=points,
            ))


# ── Main Entry Point ──────────────────────────────────────────────

def process_completed_interview(session: InterviewSession, db: Session) -> dict:
    """
    Call this after a session is completed and scored.
    Awards points, updates streak, checks badges, refreshes leaderboard.
    Returns a summary dict for the API response.
    """
    user  = session.user
    score = session.overall_score or 0

    # Points
    pts = _calculate_points(
        score,
        session.difficulty or "medium",
        session.duration_seconds or 0,
        session.num_questions or 5,
    )
    session.points_earned  = pts
    user.total_points      = (user.total_points or 0) + pts

    # Streak
    streak = _update_streak(user, db)

    # Count completed interviews
    from sqlalchemy import func
    total_completed = db.query(func.count(InterviewSession.id)).filter(
        InterviewSession.user_id == user.id,
        InterviewSession.status  == "completed",
    ).scalar() or 0

    # Badges
    new_badges = _check_badges(user, session, total_completed, streak, score, db)

    # Leaderboard
    _upsert_leaderboard(user, session, db)

    db.commit()

    return {
        "points_earned": pts,
        "total_points":  user.total_points,
        "streak":        streak,
        "new_badges":    [
            {**BADGE_DEFINITIONS.get(k, {}), "key": k}
            for k in new_badges
        ],
    }
