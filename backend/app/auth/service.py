"""
Auth v2 — Service Layer (Business Logic)
All authentication flows live here. Router calls service, service calls repository.
"""
from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import repository as repo
from app.auth.email_service import send_otp_email, send_reset_email

from app.auth.google import verify_google_token
from app.auth.rate_limiter import (
    check_login_rate, check_otp_rate,
    check_register_rate, check_resend_rate,
    check_reset_rate,
    reset_login_rate,
)

from app.auth.schemas import (
    AuthResponse, ForgotPasswordRequest, GoogleAuthRequest, LoginRequest,
    RegisterRequest, ResendOTPRequest, ResetPasswordRequest, UserResponse,
    VerifyEmailRequest,
)

from app.auth.security import (
    create_access_token, generate_otp, hash_password,
    verify_otp, verify_password,
)

logger = structlog.get_logger(__name__)

# Max OTP attempts before lockout
MAX_OTP_ATTEMPTS = 5


def _build_user_response(user) -> UserResponse:
    return UserResponse(
        user_id    = str(user.id),
        email      = user.email,
        name       = user.name,
        picture    = user.picture,
        provider   = user.provider,
        is_verified= user.is_verified,
    )


def _build_auth_response(user) -> AuthResponse:
    token, expires_in = create_access_token(
        user_id    = str(user.id),
        email      = user.email,
        provider   = user.provider,
        is_verified= user.is_verified,
    )
    return AuthResponse(
        access_token = token,
        expires_in   = expires_in,
        user         = _build_user_response(user),
    )


# ═══════════════════════════════════════════════════════════════════════
# REGISTER (Email + Password)
# ═══════════════════════════════════════════════════════════════════════

async def register(request: RegisterRequest, client_ip: str, db: AsyncSession) -> dict:
    """
    1. Rate-limit by IP
    2. Check for duplicate email
    3. Hash password
    4. Create user (is_verified=False)
    5. Generate OTP → send email
    6. Return success (no access token yet — must verify first)
    """
    # Rate limit
    allowed, retry_after = check_register_rate(client_ip)
    if not allowed:
        raise PermissionError(f"Too many registrations. Retry after {retry_after}s.")

    # Duplicate check
    existing = await repo.get_user_by_email(db, request.email)
    if existing:
        if existing.provider == "google":
            raise ValueError("This email is registered via Google. Please use Google Sign-In.")
        raise ValueError("This email is already registered. Please login.")

    # Create user
    pwd_hash = hash_password(request.password)
    user = await repo.create_user(
        db,
        email         = request.email,
        name          = request.name,
        password_hash = pwd_hash,
        provider      = "email",
        is_verified   = False,
    )

    # Generate + store OTP
    otp_plain, otp_hash = generate_otp()
    await repo.create_otp(db, user.id, otp_hash)
    await db.commit()

    # Send email (non-blocking — failure doesn't abort registration)
    email_sent = await send_otp_email(request.email, request.name, otp_plain)

    logger.info(
        "user_registered",
        user_id = str(user.id),
        email   = request.email,
        email_sent = email_sent,
    )

    return {
        "message"   : "Account created. Please check your email for the verification code.",
        "email"     : request.email,
        "email_sent": email_sent,
    }


# ═══════════════════════════════════════════════════════════════════════
# VERIFY EMAIL
# ═══════════════════════════════════════════════════════════════════════

async def verify_email(request: VerifyEmailRequest, db: AsyncSession) -> AuthResponse:
    """
    1. Fetch user by email
    2. Check rate limit on OTP attempts
    3. Fetch active OTP record
    4. Verify OTP hash
    5. Mark OTP used + mark user verified
    6. Issue JWT
    """
    user = await repo.get_user_by_email(db, request.email)
    if not user:
        raise ValueError("Account not found.")

    if user.is_verified:
        raise ValueError("Email is already verified. Please login.")

    # Rate limit OTP attempts per user
    allowed, retry_after = check_otp_rate(str(user.id))
    if not allowed:
        raise PermissionError(
            f"Too many verification attempts. Try again in {retry_after // 60 + 1} minutes."
        )

    # Fetch active OTP
    otp_record = await repo.get_active_otp(db, user.id)
    if not otp_record:
        raise ValueError("Verification code expired. Request a new one.")

    # Brute-force guard
    if otp_record.attempts >= MAX_OTP_ATTEMPTS:
        raise PermissionError("Too many attempts. Request a new verification code.")

    # Increment attempt BEFORE verifying (prevents timing oracle)
    new_attempts = await repo.increment_otp_attempts(db, otp_record.id)

    # Verify
    if not verify_otp(request.otp, otp_record.otp_hash):
        remaining = MAX_OTP_ATTEMPTS - new_attempts
        await db.commit()
        raise ValueError(
            f"Invalid verification code. {remaining} attempt{'s' if remaining != 1 else ''} remaining."
        )

    # Success — mark OTP used and user verified
    await repo.mark_otp_used(db, otp_record.id)
    await repo.mark_user_verified(db, user.id)
    await db.commit()

    # Refresh user state
    await db.refresh(user)

    logger.info("email_verified", user_id=str(user.id), email=user.email)
    return _build_auth_response(user)


# ═══════════════════════════════════════════════════════════════════════
# RESEND OTP
# ═══════════════════════════════════════════════════════════════════════

async def resend_otp(request: ResendOTPRequest, db: AsyncSession) -> dict:
    """Rate-limited OTP resend."""
    allowed, retry_after = check_resend_rate(request.email)
    if not allowed:
        raise PermissionError(
            f"Too many resend requests. Try again in {retry_after // 60 + 1} minutes."
        )

    user = await repo.get_user_by_email(db, request.email)
    if not user:
        # Don't reveal whether email exists (security)
        return {"message": "If your email is registered, a new code has been sent."}

    if user.is_verified:
        raise ValueError("Email is already verified.")

    otp_plain, otp_hash = generate_otp()
    await repo.create_otp(db, user.id, otp_hash)
    await db.commit()

    await send_otp_email(request.email, user.name or "", otp_plain)
    logger.info("otp_resent", user_id=str(user.id))
    return {"message": "A new verification code has been sent to your email."}


# ═══════════════════════════════════════════════════════════════════════
# LOGIN (Email + Password)
# ═══════════════════════════════════════════════════════════════════════

async def login(request: LoginRequest, client_ip: str, db: AsyncSession) -> AuthResponse:
    """
    1. Rate-limit by IP
    2. Fetch user
    3. Verify password
    4. Check is_verified
    5. Issue JWT
    """
    allowed, retry_after = check_login_rate(client_ip)
    if not allowed:
        raise PermissionError(f"Too many login attempts. Retry after {retry_after}s.")

    user = await repo.get_user_by_email(db, request.email)

    # Constant-time: always verify password even if user not found (prevents timing)
    password_ok = verify_password(request.password, user.password_hash) if (
        user and user.password_hash
    ) else False

    if not user or not password_ok:
        raise ValueError("Invalid email or password.")

    if user.provider == "google":
        raise ValueError("This account uses Google Sign-In. Please use the Google button.")

    if not user.is_verified:
        raise PermissionError("Please verify your email before logging in.")

    # Success — reset login rate limiter for this IP
    reset_login_rate(client_ip)
    logger.info("user_logged_in", user_id=str(user.id), provider="email")
    return _build_auth_response(user)


# ═══════════════════════════════════════════════════════════════════════
# GOOGLE AUTH
# ═══════════════════════════════════════════════════════════════════════

async def google_auth(request: GoogleAuthRequest, db: AsyncSession) -> AuthResponse:
    """
    1. Verify Google ID token server-side
    2. Create user if new, fetch if existing
    3. Issue JWT immediately (Google accounts are pre-verified)
    """
    payload = await verify_google_token(request.id_token)

    user = await repo.get_user_by_email(db, payload["email"])
    if not user:
        # Auto-create account for new Google users
        user = await repo.create_user(
            db,
            email       = payload["email"],
            name        = payload["name"],
            password_hash = None,           # No password for OAuth users
            provider    = "google",
            picture     = payload["picture"],
            is_verified = True,             # Google has verified the email
        )
        await db.commit()
        logger.info("google_user_created", email=payload["email"])
    else:
        # Update picture if changed
        if payload.get("picture") and user.picture != payload["picture"]:
            await repo.update_user_picture(db, user.id, payload["picture"])
            await db.commit()
        await db.refresh(user)
        logger.info("google_user_logged_in", email=payload["email"])

    return _build_auth_response(user)


# ═══════════════════════════════════════════════════════════════════════
# GET ME
# ═══════════════════════════════════════════════════════════════════════

async def get_me(user_id: str, db: AsyncSession) -> UserResponse:
    user = await repo.get_user_by_id(db, user_id)
    if not user:
        raise ValueError("User not found.")
    return _build_user_response(user)


# ═══════════════════════════════════════════════════════════════════════
# FORGOT PASSWORD
# ═══════════════════════════════════════════════════════════════════════

async def forgot_password(
    request: ForgotPasswordRequest, db: AsyncSession
) -> dict:
    """
    1. Look up user by email (always returns same message — no email enumeration)
    2. Validate provider (Google users can't reset password)
    3. Generate reset OTP
    4. Send password reset email
    """
    # Always same response regardless of whether email exists (prevents enumeration)
    GENERIC_MSG = "If that email is registered, you'll receive a password reset code shortly."

    allowed, retry_after = check_reset_rate(request.email)
    if not allowed:
        raise PermissionError(
            f"Too many reset requests. Try again in {retry_after // 60 + 1} minutes."
        )

    user = await repo.get_user_by_email(db, request.email)
    if not user:
        return {"message": GENERIC_MSG}   # Silent — don't reveal email doesn't exist

    if user.provider == "google":
        # For Google users: tell them to use Google Sign-In (no password to reset)
        return {"message": GENERIC_MSG}   # Still generic — don't leak provider info

    otp_plain, otp_hash = generate_otp()
    await repo.create_otp(db, user.id, otp_hash)
    await db.commit()

    await send_reset_email(request.email, user.name or "", otp_plain)
    logger.info("password_reset_requested", user_id=str(user.id))
    return {"message": GENERIC_MSG}


# ═══════════════════════════════════════════════════════════════════════
# RESET PASSWORD
# ═══════════════════════════════════════════════════════════════════════

async def reset_password(
    request: ResetPasswordRequest, db: AsyncSession
) -> dict:
    """
    1. Fetch user
    2. Rate-limit OTP attempts
    3. Verify OTP
    4. Hash + store new password
    5. Invalidate OTP
    """
    user = await repo.get_user_by_email(db, request.email)
    if not user:
        raise ValueError("Invalid reset request.")

    if user.provider == "google":
        raise ValueError("Google accounts don't use passwords. Sign in with Google.")

    # Rate-limit: reuse OTP rate limiter for reset flow too
    allowed, retry_after = check_otp_rate(str(user.id))
    if not allowed:
        raise PermissionError(
            f"Too many attempts. Try again in {retry_after // 60 + 1} minutes."
        )

    otp_record = await repo.get_active_otp(db, user.id)
    if not otp_record:
        raise ValueError("Reset code expired. Request a new one.")

    if otp_record.attempts >= MAX_OTP_ATTEMPTS:
        raise PermissionError("Too many attempts. Request a new reset code.")

    # Increment before verify (prevents timing oracle)
    new_attempts = await repo.increment_otp_attempts(db, otp_record.id)

    if not verify_otp(request.otp, otp_record.otp_hash):
        remaining = MAX_OTP_ATTEMPTS - new_attempts
        await db.commit()
        raise ValueError(
            f"Invalid reset code. {remaining} attempt{'s' if remaining != 1 else ''} remaining."
        )

    # OTP valid — update password + invalidate OTP
    new_hash = hash_password(request.new_password)
    await repo.update_password(db, user.id, new_hash)
    await repo.mark_otp_used(db, otp_record.id)
    await db.commit()

    logger.info("password_reset_success", user_id=str(user.id))
    return {"message": "Password reset successfully. You can now log in with your new password."}
