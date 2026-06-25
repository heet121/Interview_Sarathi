from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    DateTime, ForeignKey, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"
    id                  = Column(Integer, primary_key=True, index=True)
    email               = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password     = Column(String(255), nullable=False)
    full_name           = Column(String(255))
    college             = Column(String(255))
    branch              = Column(String(255))
    graduation_year     = Column(String(10))
    cgpa                = Column(String(20))
    is_active           = Column(Boolean, default=True)
    is_verified         = Column(Boolean, default=False)       # email verification
    verification_token  = Column(String(255), nullable=True)
    reset_token         = Column(String(255), nullable=True, index=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)
    # Gamification
    total_points        = Column(Integer, default=0)
    interview_streak    = Column(Integer, default=0)           # consecutive days
    last_interview_date = Column(DateTime(timezone=True), nullable=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), onupdate=func.now())
    sessions            = relationship("InterviewSession", back_populates="user", cascade="all, delete-orphan")
    resumes             = relationship("Resume",           back_populates="user", cascade="all, delete-orphan")
    badges              = relationship("UserBadge",        back_populates="user", cascade="all, delete-orphan")
    leaderboard_entries = relationship("LeaderboardEntry", back_populates="user", cascade="all, delete-orphan")


class Resume(Base):
    __tablename__ = "resumes"
    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename         = Column(String(255))
    text_content     = Column(Text)
    skills_extracted = Column(JSON)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    user             = relationship("User", back_populates="resumes")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id"), nullable=False)
    company          = Column(String(255), index=True)
    role             = Column(String(255))
    interview_type   = Column(String(50))
    difficulty       = Column(String(50))
    num_questions    = Column(Integer, default=5)
    skills_focus     = Column(Text)
    custom_focus     = Column(Text)
    duration_seconds = Column(Integer, default=0)
    overall_score    = Column(Float)
    points_earned    = Column(Integer, default=0)
    status           = Column(String(30), default="in_progress", index=True)
    started_at       = Column(DateTime(timezone=True), server_default=func.now())
    completed_at     = Column(DateTime(timezone=True))
    user             = relationship("User", back_populates="sessions")
    questions        = relationship("SessionQuestion",  back_populates="session", cascade="all, delete-orphan")
    analysis         = relationship("SessionAnalysis",  back_populates="session", uselist=False, cascade="all, delete-orphan")
    posture_logs     = relationship("PostureLog",        back_populates="session", cascade="all, delete-orphan")


class SessionQuestion(Base):
    __tablename__ = "session_questions"
    id                  = Column(Integer, primary_key=True, index=True)
    session_id          = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    question_index      = Column(Integer)
    question_text       = Column(Text)
    answer_text         = Column(Text)
    audio_file_path     = Column(String(500))
    transcript_raw      = Column(Text)
    bert_label          = Column(String(20))
    bert_score          = Column(Float)
    nlp_keywords        = Column(JSON)
    content_score       = Column(Float)
    communication_score = Column(Float)
    relevance_score     = Column(Float)
    ai_feedback         = Column(Text)
    judge_scores        = Column(JSON)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    session             = relationship("InterviewSession", back_populates="questions")


class SessionAnalysis(Base):
    __tablename__ = "session_analyses"
    id                  = Column(Integer, primary_key=True, index=True)
    session_id          = Column(Integer, ForeignKey("interview_sessions.id"), unique=True, nullable=False)
    overall_score       = Column(Float)
    verdict             = Column(String(50))
    content_score       = Column(Float)
    communication_score = Column(Float)
    confidence_score    = Column(Float)
    relevance_score     = Column(Float)
    star_score          = Column(Float)
    posture_score       = Column(Float)
    overall_summary     = Column(Text)
    strengths           = Column(JSON)
    improvements        = Column(JSON)
    roadmap             = Column(JSON)
    full_analysis_json  = Column(JSON)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    session             = relationship("InterviewSession", back_populates="analysis")


class PostureLog(Base):
    __tablename__ = "posture_logs"
    id               = Column(Integer, primary_key=True, index=True)
    session_id       = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    timestamp_sec    = Column(Float)
    mediapipe_label  = Column(String(50))
    mediapipe_eye    = Column(Boolean)
    mediapipe_conf   = Column(Float)
    deepface_emotion = Column(String(50))
    deepface_conf    = Column(Float)
    posture_label    = Column(String(50))
    eye_contact      = Column(Boolean)
    confidence_level = Column(Float)
    raw_landmarks    = Column(JSON)
    session          = relationship("InterviewSession", back_populates="posture_logs")


class QuestionBank(Base):
    __tablename__ = "question_bank"
    id          = Column(Integer, primary_key=True, index=True)
    category    = Column(String(100), index=True)
    role        = Column(String(100), index=True)
    company     = Column(String(100), index=True)
    difficulty  = Column(String(50))
    question    = Column(Text, nullable=False)
    answer_hint = Column(Text)
    tags        = Column(JSON)
    source      = Column(String(100))


# ── Gamification ──────────────────────────────────────────────────

BADGE_DEFINITIONS = {
    "first_interview":    {"name": "First Step",          "emoji": "🎯", "description": "Completed your first interview",              "points": 50},
    "streak_3":           {"name": "On a Roll",           "emoji": "🔥", "description": "3-day interview streak",                      "points": 100},
    "streak_7":           {"name": "Consistent",          "emoji": "⚡", "description": "7-day interview streak",                      "points": 250},
    "streak_30":          {"name": "Iron Will",           "emoji": "💎", "description": "30-day interview streak",                     "points": 1000},
    "score_80":           {"name": "High Achiever",       "emoji": "🌟", "description": "Scored 80+ in an interview",                  "points": 150},
    "score_90":           {"name": "Excellence",          "emoji": "🏆", "description": "Scored 90+ in an interview",                  "points": 300},
    "google_ready":       {"name": "Google Ready",        "emoji": "🔍", "description": "Completed a Google interview with 75+ score", "points": 200},
    "amazon_ready":       {"name": "Amazon Ready",        "emoji": "📦", "description": "Completed an Amazon interview with 75+ score","points": 200},
    "microsoft_ready":    {"name": "Microsoft Ready",     "emoji": "🖥️", "description": "Completed a Microsoft interview with 75+ score","points": 200},
    "10_interviews":      {"name": "Dedicated",           "emoji": "💪", "description": "Completed 10 interviews",                     "points": 300},
    "25_interviews":      {"name": "Interview Pro",       "emoji": "🎓", "description": "Completed 25 interviews",                     "points": 500},
    "all_rounder":        {"name": "All Rounder",         "emoji": "🌈", "description": "Practiced 5 different companies",             "points": 200},
    "speed_demon":        {"name": "Speed Demon",         "emoji": "⚡", "description": "Completed an interview in under 10 minutes",  "points": 100},
    "perfect_score":      {"name": "Perfectionist",       "emoji": "💯", "description": "Scored 95+ in an interview",                  "points": 500},
}


class UserBadge(Base):
    __tablename__ = "user_badges"
    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    badge_key  = Column(String(50), nullable=False)
    earned_at  = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("user_id", "badge_key", name="uq_user_badge"),)
    user       = relationship("User", back_populates="badges")


class LeaderboardEntry(Base):
    """
    Weekly + all-time leaderboard. One row per user per period.
    period: "all_time" | "YYYY-WW" (ISO week) | "YYYY-MM" (month)
    """
    __tablename__ = "leaderboard_entries"
    id             = Column(Integer, primary_key=True, index=True)
    user_id        = Column(Integer, ForeignKey("users.id"), nullable=False)
    period         = Column(String(20), nullable=False, index=True)   # e.g. "2024-W42"
    score_sum      = Column(Float, default=0)
    sessions_count = Column(Integer, default=0)
    avg_score      = Column(Float, default=0)
    points         = Column(Integer, default=0)
    rank           = Column(Integer, nullable=True)
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    __table_args__ = (UniqueConstraint("user_id", "period", name="uq_user_period"),)
    user           = relationship("User", back_populates="leaderboard_entries")


class CompanyQuestionPack(Base):
    """
    Curated question packs per company — richer than raw dataset.
    Organised by category, difficulty, interview round type.
    """
    __tablename__ = "company_question_packs"
    id            = Column(Integer, primary_key=True, index=True)
    company       = Column(String(100), nullable=False, index=True)
    round_type    = Column(String(50))    # "technical" | "hr" | "behavioral" | "system_design" | "coding"
    difficulty    = Column(String(20))    # "easy" | "medium" | "hard"
    question      = Column(Text, nullable=False)
    answer_guide  = Column(Text)          # sample strong answer for Gemini context
    tags          = Column(JSON)
    upvotes       = Column(Integer, default=0)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
