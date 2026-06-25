import base64
import random

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from database import get_db
from models.models import User, InterviewSession, SessionQuestion, Resume
from models.schemas import (
    GenerateFirstQRequest, QuestionResponse,
    SubmitAnswerRequest, AnswerFeedback,
    TranscribeRequest, TranscribeResponse,
)
from utils.auth import get_current_user
from llm_service import generate_first_question, generate_followup, llm_enabled
from scoring_service import score_answer as score_answer_unified
from stt_service import transcribe_audio
from dataset_service import get_question_pool, get_company_list
from resume_service import extract_candidate_name

router = APIRouter()

MIN_ANSWER_WORDS = 5  # reject answers shorter than this


def _get_session(session_id: int, user_id: int, db: Session) -> InterviewSession:
    s = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.user_id == user_id,
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    return s


def _session_questions(session: InterviewSession) -> list:
    """
    A STABLE, de-duplicated question list for a session.

    Returns the same ordered list on every call for a given session (seeded by
    session.id), so the first question and every follow-up map to *distinct*
    questions and never repeat — even when the LLM is unavailable and we fall
    back to the dataset.
    """
    pool = get_question_pool(session.company or "")
    seen, uniq = set(), []
    for q in pool:
        norm = " ".join((q or "").split()).strip().lower()
        if norm and norm not in seen:
            seen.add(norm)
            uniq.append(q.strip())
    random.Random(session.id).shuffle(uniq)   # deterministic per session
    return uniq


def _get_latest_resume(user_id: int, db: Session) -> Resume | None:
    return (
        db.query(Resume)
        .filter(Resume.user_id == user_id)
        .order_by(Resume.created_at.desc())
        .first()
    )


def _candidate_name(resume_text: str, user: User) -> str:
    """Prefer resume name over logged-in account name for the interviewer."""
    from_resume = extract_candidate_name(resume_text or "")
    if from_resume:
        return from_resume
    if user.full_name and user.full_name.strip():
        return user.full_name.strip()
    return (user.email or "Candidate").split("@")[0]


@router.get("/companies")
def list_companies():
    companies = get_company_list()
    # Frontend expects List[str] — extract just the name
    return {"companies": [c["name"] if isinstance(c, dict) else c for c in companies]}


@router.post("/first-question", response_model=QuestionResponse)
async def get_first_question(
    payload: GenerateFirstQRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate the opening greeting + first question.
    Auto-fetches resume from DB; caller may pass resume_text to override.
    Resume skills are extracted and used to personalise the question.
    """
    session = _get_session(payload.session_id, current_user.id, db)

    if session.status == "completed":
        raise HTTPException(status_code=400, detail="Session is already completed")

    dataset_qs = _session_questions(session)

    # Resume-aware: auto-fetch unless caller provided text
    resume = _get_latest_resume(current_user.id, db)
    resume_text   = payload.resume_text or (resume.text_content  if resume else "") or ""
    resume_skills = (resume.skills_extracted if resume else []) or []

    # Auto-fill skills_focus from resume if not already set on session
    if resume_skills and not session.skills_focus:
        session.skills_focus = ", ".join(resume_skills[:8])
        db.commit()

    cfg = {
        "name":           _candidate_name(resume_text, current_user),
        "company":        session.company,
        "role":           session.role,
        "interview_type": session.interview_type,
        "difficulty":     session.difficulty,
        "num_questions":  session.num_questions,
        "skills":         session.skills_focus,
        "focus":          session.custom_focus,
        "resume_text":    resume_text[:1500],
        "resume_skills":  resume_skills,
        "college":        current_user.college,
        "branch":         current_user.branch,
    }

    question = await generate_first_question(cfg, dataset_qs)

    existing = db.query(SessionQuestion).filter(
        SessionQuestion.session_id == session.id,
        SessionQuestion.question_index == 0,
    ).first()
    if not existing:
        db.add(SessionQuestion(
            session_id=session.id,
            question_index=0,
            question_text=question,
        ))
        db.commit()

    return QuestionResponse(
        question=question,
        question_index=0,
        is_last=(session.num_questions == 1),
        source="dataset" if (not llm_enabled() or dataset_qs) else "ai",
    )


@router.post("/submit-answer", response_model=AnswerFeedback)
async def submit_answer(
    payload: SubmitAnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit answer → validate → NLP + LLM scoring → follow-up question.

    Skipped questions bypass validation and scoring entirely but still
    advance the interview to the next question.
    """
    session = _get_session(payload.session_id, current_user.id, db)

    if session.status == "completed":
        raise HTTPException(status_code=400, detail="Session is already completed")

    # A question counts as skipped if the client flagged it, or sent the
    # sentinel / an empty answer.
    raw_answer = (payload.answer_text or "").strip()
    is_skipped = payload.skipped or raw_answer in ("", "[Skipped]")

    dataset_qs = _session_questions(session)

    if is_skipped:
        answer_text = "[Skipped]"
        scored = None
    else:
        answer_text = raw_answer
        word_count = len(answer_text.split())
        if word_count < MIN_ANSWER_WORDS:
            raise HTTPException(
                status_code=422,
                detail=f"Answer too short ({word_count} words). "
                       f"Please provide at least {MIN_ANSWER_WORDS} words."
            )
        scored = await score_answer_unified(
            payload.question_text,
            answer_text,
            session.company or "",
            session.role or "",
        )

    # Build history for follow-up
    existing_qs = (
        db.query(SessionQuestion)
        .filter(SessionQuestion.session_id == session.id)
        .order_by(SessionQuestion.question_index)
        .all()
    )
    history = []
    for q in existing_qs:
        history.append({"role": "assistant", "content": q.question_text or ""})
        if q.answer_text:
            history.append({"role": "user", "content": f"[My answer]: {q.answer_text}"})

    next_idx = payload.question_index + 1
    is_last  = next_idx >= (session.num_questions or 5)

    resume = _get_latest_resume(current_user.id, db)
    resume_text = (resume.text_content if resume else "") or ""

    cfg = {
        "name":           _candidate_name(resume_text, current_user),
        "company":        session.company,
        "role":           session.role,
        "interview_type": session.interview_type,
        "difficulty":     session.difficulty,
        "num_questions":  session.num_questions,
        "skills":         session.skills_focus,
        "focus":          session.custom_focus,
        "resume_text":    resume_text[:1500],
    }

    ai_reply = await generate_followup(
        cfg, history, answer_text, is_last, dataset_qs,
        question_index=next_idx,
    )

    if is_skipped:
        bert_label          = "skipped"
        bert_score          = None
        keywords            = []
        combined_content    = 0.0
        communication_score = 0.0
        relevance_score     = 0.0
        llm_score           = 0.0
        judge_overall       = 0.0
        judge_scores        = None
        scoring_engine      = None
        ai_feedback         = "Question skipped — no answer was given."
        quick               = "You skipped this question. Try to attempt every question next time."
    else:
        llm_score           = scored.get("llm_score") or scored["overall_score"]
        combined_content    = scored["content_score"]
        communication_score = scored["communication_score"]
        relevance_score     = scored["relevance_score"]
        ai_feedback         = scored["ai_feedback"]
        bert_label          = scored["bert_label"]
        bert_score          = scored["bert_score"]
        keywords            = scored["keywords"]
        judge_overall       = scored["judge_overall"]
        judge_scores        = scored["judge_scores"]
        scoring_engine      = scored["scoring_engine"]
        wc  = scored["word_count"]
        kws = ", ".join(keywords[:3]) if keywords else "—"
        quick = (
            f"Judge score: {judge_overall}/100 — {ai_feedback[:120]}"
            if judge_overall
            else (
                "Try to elaborate more — aim for 2–3 minutes per answer." if wc < 20
                else f"Good detail ({wc} words). Key terms: {kws}"
            )
        )

    sq = db.query(SessionQuestion).filter(
        SessionQuestion.session_id == session.id,
        SessionQuestion.question_index == payload.question_index,
    ).first()

    if sq:
        sq.answer_text         = answer_text
        sq.bert_label          = bert_label
        sq.bert_score          = bert_score
        sq.nlp_keywords        = keywords
        sq.content_score       = combined_content
        sq.communication_score = communication_score
        sq.relevance_score     = relevance_score
        sq.ai_feedback         = ai_feedback
        sq.judge_scores        = judge_scores
    else:
        sq = SessionQuestion(
            session_id=session.id,
            question_index=payload.question_index,
            question_text=payload.question_text,
            answer_text=answer_text,
            bert_label=bert_label,
            bert_score=bert_score,
            nlp_keywords=keywords,
            content_score=combined_content,
            communication_score=communication_score,
            relevance_score=relevance_score,
            ai_feedback=ai_feedback,
            judge_scores=judge_scores,
        )
        db.add(sq)

    if not is_last:
        next_sq = db.query(SessionQuestion).filter(
            SessionQuestion.session_id == session.id,
            SessionQuestion.question_index == next_idx,
        ).first()
        if not next_sq:
            db.add(SessionQuestion(
                session_id=session.id,
                question_index=next_idx,
                question_text=ai_reply,
            ))

    db.commit()

    return AnswerFeedback(
        ai_reply=ai_reply,
        bert_label=bert_label,
        bert_score=bert_score,
        keywords=keywords,
        quick_feedback=quick,
        llm_score=llm_score,
        llm_feedback=ai_feedback,
        content_score=combined_content,
        communication_score=communication_score,
        relevance_score=relevance_score,
        judge_overall=judge_overall,
        judge_scores=judge_scores,
        scoring_engine=scoring_engine,
        question_index=next_idx,
        is_last=is_last,
    )


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(payload: TranscribeRequest):
    try:
        text = await transcribe_audio(payload.audio_base64, payload.mime_type)
        return TranscribeResponse(transcript=text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.post("/transcribe-file", response_model=TranscribeResponse)
async def transcribe_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    content   = await file.read()
    audio_b64 = base64.b64encode(content).decode()
    text = await transcribe_audio(audio_b64, file.content_type or "audio/webm")
    return TranscribeResponse(transcript=text)
