from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime


# ── Auth ──────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    college: Optional[str] = None
    branch: Optional[str] = None
    graduation_year: Optional[str] = None
    cgpa: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    college: Optional[str] = None
    branch: Optional[str] = None
    graduation_year: Optional[str] = None
    cgpa: Optional[str] = None
    is_active: bool
    total_points: Optional[int] = 0
    interview_streak: Optional[int] = 0

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    college: Optional[str] = None
    branch: Optional[str] = None
    graduation_year: Optional[str] = None
    cgpa: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Password Reset ────────────────────────────────────────────────

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# ── Resume ────────────────────────────────────────────────────────
class ResumeOut(BaseModel):
    id: int
    filename: Optional[str] = None
    skills_extracted: Optional[List[str]] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Sessions ─────────────────────────────────────────────────────
class SessionCreate(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    interview_type: Optional[str] = "technical"
    difficulty: Optional[str] = "medium"
    num_questions: Optional[int] = 5
    skills_focus: Optional[str] = None
    custom_focus: Optional[str] = None


class SessionOut(BaseModel):
    id: int
    user_id: int
    company: Optional[str] = None
    role: Optional[str] = None
    interview_type: Optional[str] = None
    difficulty: Optional[str] = None
    num_questions: Optional[int] = None
    status: str
    overall_score: Optional[float] = None
    started_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Interview ─────────────────────────────────────────────────────
class GenerateFirstQRequest(BaseModel):
    session_id: int
    resume_text: Optional[str] = None   # still accepted for manual override


class QuestionResponse(BaseModel):
    question: str
    question_index: int
    is_last: bool
    source: Optional[str] = "ai"        # "dataset" | "ai"


class SubmitAnswerRequest(BaseModel):
    session_id: int
    question_index: int
    question_text: str
    answer_text: str
    skipped: Optional[bool] = False


class AnswerFeedback(BaseModel):
    ai_reply: str
    bert_label: Optional[str] = None
    bert_score: Optional[float] = None
    keywords: Optional[List[str]] = []
    quick_feedback: Optional[str] = None
    llm_score: Optional[float] = None
    llm_feedback: Optional[str] = None
    content_score: Optional[float] = None
    communication_score: Optional[float] = None
    relevance_score: Optional[float] = None
    judge_overall: Optional[float] = None
    judge_scores: Optional[Dict[str, float]] = None
    scoring_engine: Optional[str] = None
    question_index: Optional[int] = None
    is_last: Optional[bool] = False


class TranscribeRequest(BaseModel):
    audio_base64: str
    mime_type: Optional[str] = "audio/webm"


class TranscribeResponse(BaseModel):
    transcript: str


# ── Posture ───────────────────────────────────────────────────────
class PostureFrameRequest(BaseModel):
    session_id: int
    frame_base64: str
    timestamp_sec: Optional[float] = 0.0
    landmarks: Optional[Dict] = None


class PostureResult(BaseModel):
    posture_label: str
    eye_contact: bool
    confidence_level: float
    emotion: Optional[str] = None
    feedback: Optional[str] = None


# ── Analysis ──────────────────────────────────────────────────────
class AnalysisResult(BaseModel):
    overall_score: float
    verdict: str
    overall_summary: str
    strengths: List[str] = []
    improvements: List[str] = []
    dimensions: Dict[str, Any] = {}
    qa_breakdown: List[Dict[str, Any]] = []
    roadmap: List[str] = []
    posture_score: Optional[float] = None
    posture_summary: Optional[str] = None
    gamification: Optional[Dict[str, Any]] = None

    model_config = {"extra": "allow"}
