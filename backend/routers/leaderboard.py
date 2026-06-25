from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from database import get_db
from models.models import User, InterviewSession, LeaderboardEntry
from utils.auth import get_current_user

router = APIRouter()

_LIMIT = 50   # max entries returned


def _week_key()  -> str: return date.today().strftime("%G-W%V")
def _month_key() -> str: return date.today().strftime("%Y-%m")


def _build_entry(entry: LeaderboardEntry, rank: int, current_user_id: int) -> dict:
    u = entry.user
    return {
        "rank":            rank,
        "user_id":         u.id,
        "full_name":       u.full_name or "Anonymous",
        "college":         u.college,
        "avatar_initial":  (u.full_name or u.email or "?")[0].upper(),
        "avg_score":       round(entry.avg_score or 0, 1),
        "sessions_count":  entry.sessions_count,
        "points":          entry.points,
        "streak":          u.interview_streak or 0,
        "badges_count":    len(u.badges),
        "is_me":           u.id == current_user_id,
    }


def _get_leaderboard(period: str, db: Session, current_user_id: int, limit: int = _LIMIT):
    entries = (
        db.query(LeaderboardEntry)
        .filter(LeaderboardEntry.period == period)
        .join(LeaderboardEntry.user)
        .filter(User.is_active == True)
        .order_by(desc(LeaderboardEntry.avg_score), desc(LeaderboardEntry.sessions_count))
        .limit(limit)
        .all()
    )
    return [_build_entry(e, i+1, current_user_id) for i, e in enumerate(entries)]


@router.get("/weekly")
def weekly_leaderboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Top performers this week (Monday–Sunday)."""
    data  = _get_leaderboard(_week_key(), db, current_user.id)
    my_entry = next((e for e in data if e["is_me"]), None)
    return {
        "period":       "weekly",
        "week":         _week_key(),
        "leaderboard":  data,
        "my_entry":     my_entry,
        "total_players":len(data),
    }


@router.get("/monthly")
def monthly_leaderboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Top performers this month."""
    data = _get_leaderboard(_month_key(), db, current_user.id)
    my_entry = next((e for e in data if e["is_me"]), None)
    return {
        "period":       "monthly",
        "month":        _month_key(),
        "leaderboard":  data,
        "my_entry":     my_entry,
        "total_players":len(data),
    }


@router.get("/all-time")
def alltime_leaderboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """All-time hall of fame."""
    data = _get_leaderboard("all_time", db, current_user.id)
    my_entry = next((e for e in data if e["is_me"]), None)
    return {
        "period":       "all_time",
        "leaderboard":  data,
        "my_entry":     my_entry,
        "total_players":len(data),
    }


@router.get("/company")
def company_leaderboard(
    company: str = Query(..., description="Company name e.g. Google"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Top scorers for a specific company (all-time best score)."""
    rows = (
        db.query(
            InterviewSession.user_id,
            func.max(InterviewSession.overall_score).label("best_score"),
            func.count(InterviewSession.id).label("sessions"),
            func.avg(InterviewSession.overall_score).label("avg_score"),
        )
        .filter(
            InterviewSession.company.ilike(f"%{company}%"),
            InterviewSession.status       == "completed",
            InterviewSession.overall_score.isnot(None),
        )
        .group_by(InterviewSession.user_id)
        .order_by(desc("best_score"))
        .limit(_LIMIT)
        .all()
    )

    leaderboard = []
    for rank, (user_id, best, sessions, avg) in enumerate(rows, 1):
        u = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not u:
            continue
        leaderboard.append({
            "rank":           rank,
            "user_id":        user_id,
            "full_name":      u.full_name or "Anonymous",
            "college":        u.college,
            "avatar_initial": (u.full_name or u.email or "?")[0].upper(),
            "best_score":     round(best, 1),
            "avg_score":      round(avg, 1),
            "sessions":       sessions,
            "streak":         u.interview_streak or 0,
            "is_me":          user_id == current_user.id,
        })

    my_entry = next((e for e in leaderboard if e["is_me"]), None)
    return {
        "company":      company,
        "leaderboard":  leaderboard,
        "my_entry":     my_entry,
    }


@router.get("/college")
def college_leaderboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rankings within the current user's college."""
    if not current_user.college:
        return {"message": "Set your college in profile to see college rankings", "leaderboard": []}

    entries = (
        db.query(LeaderboardEntry)
        .filter(LeaderboardEntry.period == "all_time")
        .join(LeaderboardEntry.user)
        .filter(
            User.college.ilike(f"%{current_user.college}%"),
            User.is_active == True,
        )
        .order_by(desc(LeaderboardEntry.avg_score))
        .limit(_LIMIT)
        .all()
    )

    leaderboard = [_build_entry(e, i+1, current_user.id) for i, e in enumerate(entries)]
    my_entry    = next((e for e in leaderboard if e["is_me"]), None)
    return {
        "college":      current_user.college,
        "leaderboard":  leaderboard,
        "my_entry":     my_entry,
        "total_peers":  len(leaderboard),
    }


@router.get("/me")
def my_ranks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """My rank across weekly, monthly, all-time, and college leaderboards."""
    def _my_rank(period: str) -> dict | None:
        all_entries = (
            db.query(LeaderboardEntry)
            .filter(LeaderboardEntry.period == period)
            .join(LeaderboardEntry.user)
            .filter(User.is_active == True)
            .order_by(desc(LeaderboardEntry.avg_score))
            .all()
        )
        for i, e in enumerate(all_entries):
            if e.user_id == current_user.id:
                return {
                    "rank":         i + 1,
                    "total":        len(all_entries),
                    "percentile":   round((1 - i / len(all_entries)) * 100, 1) if all_entries else 0,
                    "avg_score":    round(e.avg_score or 0, 1),
                    "sessions":     e.sessions_count,
                    "points":       e.points,
                }
        return None

    return {
        "weekly":   _my_rank(_week_key()),
        "monthly":  _my_rank(_month_key()),
        "all_time": _my_rank("all_time"),
        "points":   current_user.total_points or 0,
        "streak":   current_user.interview_streak or 0,
        "badges":   len(current_user.badges),
    }
