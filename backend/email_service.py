import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import settings

logger = logging.getLogger(__name__)


def _build_reset_email(to_email: str, reset_url: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Interview Sarathi — Reset Your Password"
    msg["From"]    = settings.EMAIL_FROM
    msg["To"]      = to_email

    plain = f"""Hi,

You requested a password reset for your Interview Sarathi account.

Click the link below to reset your password (valid for 1 hour):
{reset_url}

If you did not request this, you can safely ignore this email.

— Interview Sarathi Team
"""

    html = f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; background: #f4f4f4; padding: 30px;">
  <div style="max-width: 480px; margin: auto; background: white; border-radius: 8px;
              padding: 32px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
    <h2 style="color: #4f46e5; margin-top: 0;">Reset Your Password</h2>
    <p style="color: #374151;">
      You requested a password reset for your <strong>Interview Sarathi</strong> account.
    </p>
    <p style="color: #374151;">
      Click the button below to set a new password. This link expires in <strong>1 hour</strong>.
    </p>
    <a href="{reset_url}"
       style="display: inline-block; margin: 20px 0; padding: 12px 28px;
              background: #4f46e5; color: white; border-radius: 6px;
              text-decoration: none; font-weight: bold;">
      Reset Password
    </a>
    <p style="color: #6b7280; font-size: 13px;">
      Or copy this link:<br>
      <a href="{reset_url}" style="color: #4f46e5; word-break: break-all;">{reset_url}</a>
    </p>
    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
    <p style="color: #9ca3af; font-size: 12px;">
      If you did not request this, you can safely ignore this email.
    </p>
  </div>
</body>
</html>
"""
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))
    return msg


def send_password_reset_email(to_email: str, token: str) -> None:
    """
    Send a password-reset email.
    Falls back to console logging when SMTP is not configured (local dev).
    """
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    if not settings.SMTP_HOST:
        # ── Console fallback (local dev / no email config) ────────
        logger.warning("SMTP not configured — printing reset link to console.")
        print("\n" + "="*60)
        print("  PASSWORD RESET LINK (no SMTP configured)")
        print(f"  Email : {to_email}")
        print(f"  Link  : {reset_url}")
        print("="*60 + "\n")
        return

    # ── Real SMTP send ─────────────────────────────────────────────
    msg = _build_reset_email(to_email, reset_url)
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, to_email, msg.as_string())
        logger.info(f"Password reset email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send reset email to {to_email}: {e}")
        raise
