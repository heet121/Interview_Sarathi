from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from database import get_db
from models.models import User, InterviewSession
from models.schemas import SessionCreate, SessionOut
from utils.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=SessionOut, status_code=201)
def create_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = InterviewSession(
        user_id=current_user.id,
        company=payload.company,
        role=payload.role,
        interview_type=payload.interview_type,
        difficulty=payload.difficulty,
        num_questions=payload.num_questions,
        skills_focus=payload.skills_focus,
        custom_focus=payload.custom_focus,
        status="in_progress",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/", response_model=List[SessionOut])
def list_sessions(
    skip: int = 0, limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == current_user.id)
        .order_by(InterviewSession.started_at.desc())
        .offset(skip).limit(limit).all()
    )


@router.get("/{session_id}")
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    questions = sorted(session.questions, key=lambda q: q.question_index or 0)
    return {
        "session": SessionOut.model_validate(session),
        "questions": [
            {
                "question_index": q.question_index,
                "question_text": q.question_text,
                "answer_text": q.answer_text,
                "bert_label": q.bert_label,
                "bert_score": q.bert_score,
                "content_score": q.content_score,
                "communication_score": q.communication_score,
                "relevance_score": getattr(q, "relevance_score", None),
                "judge_scores": q.judge_scores,
                "ai_feedback": q.ai_feedback,
                "keywords": q.nlp_keywords or [],
            }
            for q in questions
        ],
        "analysis": session.analysis.full_analysis_json if session.analysis else None,
    }


@router.patch("/{session_id}/complete")
def complete_session(
    session_id: int,
    duration_seconds: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = "completed"
    session.duration_seconds = duration_seconds
    session.completed_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Session completed"}


@router.delete("/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"message": "Session deleted"}
