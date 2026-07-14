"""
Outbound email — currently just the forgot-password reset link.

Uses Python's stdlib smtplib/email so no extra dependency is needed —
this works with Gmail (app password), Outlook, SendGrid's SMTP relay,
or an internal RINL mail server, by just setting SMTP_* in .env.

If SMTP isn't configured (SMTP_HOST/SMTP_USER/SMTP_PASSWORD blank), the
reset link is printed to the console instead. This keeps register/login/
forgot-password fully testable with zero mail setup, and is what Day 2
runs on by default.
"""

import smtplib
from email.message import EmailMessage

from app.core.config import settings


def _build_reset_link(token: str) -> str:
    return f"{settings.FRONTEND_ORIGIN}/reset-password?token={token}"


def _console_fallback(to_email: str, reset_link: str) -> None:
    print(
        "[NewsPulse] SMTP not configured — logging reset link instead of emailing.\n"
        f"[NewsPulse] Password reset link for {to_email}: {reset_link}"
    )


def send_password_reset_email(to_email: str, token: str) -> None:
    reset_link = _build_reset_link(token)

    if not settings.SMTP_CONFIGURED:
        _console_fallback(to_email, reset_link)
        return

    message = EmailMessage()
    message["Subject"] = "Reset your NewsPulse password"
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = to_email
    message.set_content(
        "We received a request to reset your NewsPulse password.\n\n"
        f"Reset it here (valid for 30 minutes): {reset_link}\n\n"
        "If you didn't request this, you can safely ignore this email."
    )
    message.add_alternative(
        f"""\
<html>
  <body style="font-family: Arial, sans-serif; color: #14181d;">
    <p>We received a request to reset your NewsPulse password.</p>
    <p>
      <a href="{reset_link}"
         style="background:#14181d;color:#ffffff;padding:10px 18px;
                text-decoration:none;border-radius:6px;display:inline-block;">
        Reset password
      </a>
    </p>
    <p>This link is valid for 30 minutes. If you didn't request this,
       you can safely ignore this email.</p>
  </body>
</html>
""",
        subtype="html",
    )

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(message)
    except Exception as exc:
        # Never let a mail-server hiccup surface as a 500 to the user, and
        # never leak whether the address exists — log it, and the caller's
        # generic "if an account exists…" response still goes out as usual.
        print(f"[NewsPulse] Failed to send reset email to {to_email}: {exc}")
        _console_fallback(to_email, reset_link)
