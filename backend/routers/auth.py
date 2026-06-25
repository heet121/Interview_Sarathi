import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
import httpx

from database import get_db
from models.models import User
from models.schemas import (
    UserCreate, UserLogin, UserOut, UserUpdate, Token,
    ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest,
)
from utils.auth import hash_password, verify_password, create_access_token, get_current_user
from email_service import send_password_reset_email
from config import settings

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)

RESET_TOKEN_EXPIRE_HOURS = 1

_ALLOWED_FRONTEND_ORIGINS = {
    settings.FRONTEND_URL.rstrip("/"),
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
}


def _resolve_frontend_base(frontend: Optional[str], state: Optional[str]) -> str:
    """Return the SPA origin to redirect to after OAuth (must be allowlisted)."""
    for candidate in (state, frontend, settings.FRONTEND_URL):
        if not candidate:
            continue
        base = candidate.strip().rstrip("/")
        if base in _ALLOWED_FRONTEND_ORIGINS:
            return base
    return settings.FRONTEND_URL.rstrip("/")


def _oauth_error_redirect(frontend_base: str, provider: str) -> RedirectResponse:
    return RedirectResponse(f"{frontend_base}/login?{urlencode({'error': f'{provider}_failed'})}")


def _oauth_success_redirect(frontend_base: str, jwt: str) -> RedirectResponse:
    return RedirectResponse(f"{frontend_base}/oauth-callback?{urlencode({'token': jwt})}")


# ── Register ──────────────────────────────────────────────────────
@router.post("/register", response_model=Token, status_code=201)
@limiter.limit(settings.RATE_LIMIT_REGISTER)
def register(request: Request, payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        college=payload.college,
        branch=payload.branch,
        graduation_year=payload.graduation_year,
        cgpa=payload.cgpa,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token, user=UserOut.model_validate(user))


# ── Login ─────────────────────────────────────────────────────────
@router.post("/login", response_model=Token)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def login(request: Request, payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token, user=UserOut.model_validate(user))


# ── Profile ───────────────────────────────────────────────────────
@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for key, val in payload.model_dump(exclude_none=True).items():
        setattr(current_user, key, val)
    db.commit()
    db.refresh(current_user)
    return current_user


# ── Change Password (logged-in user) ─────────────────────────────
@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change password for an already authenticated user."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail="New password must differ from current password")

    current_user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password changed successfully"}


# ── Forgot / Reset Password ───────────────────────────────────────
@router.post("/forgot-password")
@limiter.limit(settings.RATE_LIMIT_FORGOT_PASSWORD)
def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == payload.email).first()
    if user and user.is_active:
        token = secrets.token_urlsafe(32)
        user.reset_token         = token
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS)
        db.commit()
        try:
            send_password_reset_email(user.email, token)
        except Exception:
            pass  # don't expose email errors
    return {"message": "If that email is registered, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user = db.query(User).filter(User.reset_token == payload.token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    now     = datetime.now(timezone.utc)
    expires = user.reset_token_expires
    if expires and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if not expires or now > expires:
        raise HTTPException(status_code=400, detail="Reset token has expired. Please request a new one.")

    user.hashed_password     = hash_password(payload.new_password)
    user.reset_token         = None
    user.reset_token_expires = None
    db.commit()
    return {"message": "Password updated successfully. You can now log in."}


# ── Google OAuth ──────────────────────────────────────────────────
@router.get("/oauth/google")
def oauth_google_redirect(frontend: Optional[str] = None):
    """Redirect the user to Google's OAuth consent screen."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google OAuth is not configured")
    frontend_base = _resolve_frontend_base(frontend, None)
    params = urlencode({
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "state": frontend_base,
    })
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


@router.get("/oauth/google/callback")
async def oauth_google_callback(
    db: Session = Depends(get_db),
    code: Optional[str] = None,
    error: Optional[str] = None,
    state: Optional[str] = None,
):
    """Exchange Google auth code for user info and return a JWT."""
    frontend_base = _resolve_frontend_base(None, state)
    if error or not code:
        logger.warning(f"Google OAuth denied or missing code: error={error}")
        return _oauth_error_redirect(frontend_base, "google")

    if not settings.GOOGLE_CLIENT_ID:
        return _oauth_error_redirect(frontend_base, "google")

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            token_resp = await client.post("https://oauth2.googleapis.com/token", data={
                "code":          code,
                "client_id":     settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri":  settings.GOOGLE_REDIRECT_URI,
                "grant_type":    "authorization_code",
            })
            if token_resp.status_code != 200:
                logger.error(f"Google token exchange failed: {token_resp.status_code} {token_resp.text[:300]}")
                return _oauth_error_redirect(frontend_base, "google")
            access_token = token_resp.json().get("access_token")
            if not access_token:
                return _oauth_error_redirect(frontend_base, "google")

            info_resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if info_resp.status_code != 200:
                logger.error(f"Google userinfo failed: {info_resp.status_code}")
                return _oauth_error_redirect(frontend_base, "google")
            info = info_resp.json()
    except Exception as e:
        logger.exception(f"Google OAuth callback error: {e}")
        return _oauth_error_redirect(frontend_base, "google")

    email     = info.get("email")
    full_name = info.get("name", "")
    if not email:
        return _oauth_error_redirect(frontend_base, "google")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            hashed_password=hash_password(secrets.token_urlsafe(32)),
            full_name=full_name,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    jwt = create_access_token({"sub": str(user.id)})
    return _oauth_success_redirect(frontend_base, jwt)


# ── GitHub OAuth ──────────────────────────────────────────────────
@router.get("/oauth/github")
def oauth_github_redirect(frontend: Optional[str] = None):
    """Redirect the user to GitHub's OAuth consent screen."""
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(status_code=501, detail="GitHub OAuth is not configured")
    frontend_base = _resolve_frontend_base(frontend, None)
    params = urlencode({
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_REDIRECT_URI,
        "scope": "user:email",
        "state": frontend_base,
    })
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{params}")


@router.get("/oauth/github/callback")
async def oauth_github_callback(
    db: Session = Depends(get_db),
    code: Optional[str] = None,
    error: Optional[str] = None,
    state: Optional[str] = None,
):
    """Exchange GitHub auth code for user info and return a JWT."""
    frontend_base = _resolve_frontend_base(None, state)
    if error or not code:
        return _oauth_error_redirect(frontend_base, "github")

    if not settings.GITHUB_CLIENT_ID:
        return _oauth_error_redirect(frontend_base, "github")

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            token_resp = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id":     settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code":          code,
                    "redirect_uri":  settings.GITHUB_REDIRECT_URI,
                },
            )
            access_token = token_resp.json().get("access_token")
            if not access_token:
                logger.error(f"GitHub token exchange failed: {token_resp.text[:300]}")
                return _oauth_error_redirect(frontend_base, "github")

            user_resp = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            gh_user = user_resp.json()

            email = gh_user.get("email")
            if not email:
                emails_resp = await client.get(
                    "https://api.github.com/user/emails",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                for e in emails_resp.json():
                    if e.get("primary") and e.get("verified"):
                        email = e["email"]
                        break
    except Exception as e:
        logger.exception(f"GitHub OAuth callback error: {e}")
        return _oauth_error_redirect(frontend_base, "github")

    if not email:
        return _oauth_error_redirect(frontend_base, "github")

    full_name = gh_user.get("name") or gh_user.get("login", "")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            hashed_password=hash_password(secrets.token_urlsafe(32)),
            full_name=full_name,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    jwt = create_access_token({"sub": str(user.id)})
    return _oauth_success_redirect(frontend_base, jwt)
