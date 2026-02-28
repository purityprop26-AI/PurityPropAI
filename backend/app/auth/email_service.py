"""
Auth v2 — Email Service (OTP Delivery)

Sends OTP emails via SMTP (Gmail / Outlook / any SMTP relay).
Falls back gracefully → prints OTP to console in development.

Required env vars (at least one approach):
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM

For Gmail: enable "App Password" (not normal password) in Google Account Security.
For Resend: set RESEND_API_KEY (uses Resend HTTP API, no SMTP config needed).
"""
from __future__ import annotations

import os
import smtplib
import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

# ── Config ─────────────────────────────────────────────────────────────
SMTP_HOST  = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT  = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER  = os.getenv("SMTP_USER", "")
SMTP_PASS  = os.getenv("SMTP_PASS", "")
SMTP_FROM  = os.getenv("SMTP_FROM", SMTP_USER)
APP_NAME   = "PurityProp AI"
IS_DEV     = os.getenv("DEBUG", "false").lower() == "true"


# ── HTML email template ────────────────────────────────────────────────
def _build_otp_html(name: str, otp: str) -> str:
    first_name = (name or "there").split()[0]
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Email Verification — {APP_NAME}</title>
</head>
<body style="margin:0;padding:0;background:#0B132B;font-family:'Segoe UI',Arial,sans-serif;">
  <div style="max-width:520px;margin:40px auto;background:#1A2332;border-radius:16px;
              border:1px solid rgba(156,163,175,0.15);overflow:hidden;
              box-shadow:0 8px 32px rgba(0,0,0,0.4);">
    <!-- Header -->
    <div style="background:linear-gradient(135deg,#1e3a5f,#0B132B);padding:32px;text-align:center;">
      <h1 style="color:#fff;margin:0;font-size:24px;letter-spacing:-0.5px;">{APP_NAME}</h1>
      <p style="color:#9CA3AF;margin:8px 0 0;font-size:14px;">Real Estate Intelligence Platform</p>
    </div>
    <!-- Body -->
    <div style="padding:40px 32px;">
      <h2 style="color:#fff;margin:0 0 12px;font-size:20px;">Verify your email, {first_name} 👋</h2>
      <p style="color:#D1D5DB;font-size:15px;line-height:1.6;margin:0 0 28px;">
        Use the verification code below to complete your registration.
        This code expires in <strong style="color:#9CA3AF;">10 minutes</strong>.
      </p>
      <!-- OTP Box -->
      <div style="background:#0B132B;border:2px solid rgba(156,163,175,0.2);
                  border-radius:12px;padding:24px;text-align:center;margin-bottom:28px;">
        <p style="color:#9CA3AF;font-size:13px;margin:0 0 12px;text-transform:uppercase;
                  letter-spacing:2px;">Verification Code</p>
        <p style="color:#fff;font-size:42px;font-weight:700;letter-spacing:10px;margin:0;
                  font-family:monospace;">{otp}</p>
      </div>
      <p style="color:#64748B;font-size:13px;line-height:1.6;margin:0;">
        If you didn't request this, you can safely ignore this email.<br>
        Do not share this code with anyone.
      </p>
    </div>
    <!-- Footer -->
    <div style="padding:20px 32px;border-top:1px solid rgba(156,163,175,0.1);text-align:center;">
      <p style="color:#64748B;font-size:12px;margin:0;">
        © 2026 {APP_NAME} — Tamil Nadu Real Estate Intelligence
      </p>
    </div>
  </div>
</body>
</html>
"""


# ── SMTP sender (runs in thread pool — smtplib is synchronous) ─────────
def _send_smtp(to_email: str, subject: str, html_body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{APP_NAME} <{SMTP_FROM}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_FROM, to_email, msg.as_string())


# ── Public API ─────────────────────────────────────────────────────────
async def send_otp_email(to_email: str, name: str, otp: str) -> bool:
    """
    Send OTP verification email asynchronously.
    Returns True on success, False on failure (never raises).
    """
    subject   = f"Your {APP_NAME} verification code: {otp}"
    html_body = _build_otp_html(name, otp)

    # Development mode — print to console instead of sending email
    if IS_DEV and not SMTP_USER:
        logger.info(
            "otp_email_dev_mode",
            to=to_email,
            otp=otp,
            note="Set SMTP_USER/SMTP_PASS in .env to send real emails",
        )
        print(f"\n{'='*50}")
        print(f"📧 OTP EMAIL (DEV MODE — not actually sent)")
        print(f"   To:  {to_email}")
        print(f"   OTP: {otp}")
        print(f"{'='*50}\n")
        return True

    try:
        await asyncio.get_event_loop().run_in_executor(
            None, _send_smtp, to_email, subject, html_body
        )
        logger.info("otp_email_sent", to=to_email)
        return True
    except Exception as e:
        logger.error("otp_email_failed", to=to_email, error=str(e))
        return False


def _build_reset_html(name: str, otp: str) -> str:
    first_name = (name or "there").split()[0]
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Password Reset — {APP_NAME}</title>
</head>
<body style="margin:0;padding:0;background:#0B132B;font-family:'Segoe UI',Arial,sans-serif;">
  <div style="max-width:520px;margin:40px auto;background:#1A2332;border-radius:16px;
              border:1px solid rgba(156,163,175,0.15);overflow:hidden;
              box-shadow:0 8px 32px rgba(0,0,0,0.4);">
    <!-- Header -->
    <div style="background:linear-gradient(135deg,#3d1a1a,#1a0f0f);padding:32px;text-align:center;">
      <h1 style="color:#fff;margin:0;font-size:24px;letter-spacing:-0.5px;">{APP_NAME}</h1>
      <p style="color:#F87171;margin:8px 0 0;font-size:14px;">🔒 Password Reset Request</p>
    </div>
    <!-- Body -->
    <div style="padding:40px 32px;">
      <h2 style="color:#fff;margin:0 0 12px;font-size:20px;">Reset your password, {first_name}</h2>
      <p style="color:#D1D5DB;font-size:15px;line-height:1.6;margin:0 0 28px;">
        We received a request to reset your password. Use the code below to proceed.
        This code expires in <strong style="color:#F87171;">10 minutes</strong>.
      </p>
      <!-- OTP Box -->
      <div style="background:#0B132B;border:2px solid rgba(239,68,68,0.3);
                  border-radius:12px;padding:24px;text-align:center;margin-bottom:28px;">
        <p style="color:#F87171;font-size:13px;margin:0 0 12px;text-transform:uppercase;
                  letter-spacing:2px;">Reset Code</p>
        <p style="color:#fff;font-size:42px;font-weight:700;letter-spacing:10px;margin:0;
                  font-family:monospace;">{otp}</p>
      </div>
      <p style="color:#64748B;font-size:13px;line-height:1.6;margin:0;">
        ⚠️ If you didn't request a password reset, please ignore this email.<br>
        Your password will remain unchanged. Do not share this code.
      </p>
    </div>
    <!-- Footer -->
    <div style="padding:20px 32px;border-top:1px solid rgba(156,163,175,0.1);text-align:center;">
      <p style="color:#64748B;font-size:12px;margin:0;">
        © 2026 {APP_NAME} — Tamil Nadu Real Estate Intelligence
      </p>
    </div>
  </div>
</body>
</html>
"""


async def send_reset_email(to_email: str, name: str, otp: str) -> bool:
    """
    Send password reset OTP email.
    Returns True on success, False on failure (never raises).
    """
    subject   = f"Reset your {APP_NAME} password — code: {otp}"
    html_body = _build_reset_html(name, otp)

    if IS_DEV and not SMTP_USER:
        print(f"\n{'='*50}")
        print(f"🔒 RESET EMAIL (DEV MODE)")
        print(f"   To:  {to_email}")
        print(f"   OTP: {otp}")
        print(f"{'='*50}\n")
        return True

    try:
        await asyncio.get_event_loop().run_in_executor(
            None, _send_smtp, to_email, subject, html_body
        )
        logger.info("reset_email_sent", to=to_email)
        return True
    except Exception as e:
        logger.error("reset_email_failed", to=to_email, error=str(e))
        return False

