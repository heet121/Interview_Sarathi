import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.models import User, Resume
from models.schemas import ResumeOut
from utils.auth import get_current_user
from resume_service import extract_text_from_file

router = APIRouter()

# Allowed MIME types
ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
}


@router.post("/upload", response_model=ResumeOut, status_code=201)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a resume (PDF / DOCX / TXT).
    Extracts text and skills automatically, stores in DB.
    """
    # ── Size check ────────────────────────────────────────────────
    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_MB} MB.",
        )

    # ── Type check ────────────────────────────────────────────────
    ct = (file.content_type or "").lower()
    fname = file.filename or "resume"
    if ct not in ALLOWED_TYPES and not fname.lower().endswith((".pdf", ".docx", ".doc", ".txt")):
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Please upload a PDF, DOCX, or TXT file.",
        )

    # ── Extract text + skills ─────────────────────────────────────
    try:
        text, skills = extract_text_from_file(fname, content)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not text or len(text.strip()) < 50:
        raise HTTPException(
            status_code=422,
            detail="Could not extract meaningful text from the file. "
                   "Make sure the PDF is not scanned/image-only.",
        )

    # ── Save file to disk (optional — for future retrieval) ───────
    upload_path = os.path.join(settings.UPLOAD_DIR, f"user_{current_user.id}_{fname}")
    try:
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        with open(upload_path, "wb") as f_out:
            f_out.write(content)
    except Exception as e:
        # Non-fatal — we still have text in DB
        upload_path = None

    # ── Save to DB ────────────────────────────────────────────────
    resume = Resume(
        user_id=current_user.id,
        filename=fname,
        text_content=text,
        skills_extracted=skills,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.get("/latest")
def get_latest_resume(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return the most recently uploaded resume for the current user,
    including the full extracted text (used by the interview flow).
    """
    resume = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .first()
    )
    if not resume:
        return {"resume": None, "message": "No resume uploaded yet"}
    return {
        "id":               resume.id,
        "filename":         resume.filename,
        "text_content":     resume.text_content,
        "skills_extracted": resume.skills_extracted,
        "created_at":       resume.created_at,
    }


@router.get("/", response_model=List[ResumeOut])
def list_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all resumes for the current user (metadata only, no full text)."""
    return (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .all()
    )


@router.get("/{resume_id}")
def get_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific resume including full text."""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id,
    ).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {
        "id":               resume.id,
        "filename":         resume.filename,
        "text_content":     resume.text_content,
        "skills_extracted": resume.skills_extracted,
        "created_at":       resume.created_at,
    }


@router.delete("/{resume_id}", status_code=204)
def delete_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a resume."""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id,
    ).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    db.delete(resume)
    db.commit()
