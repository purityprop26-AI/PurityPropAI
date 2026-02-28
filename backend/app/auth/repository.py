"""
Auth v2 — Repository (Database Operations)
All raw DB queries are here. Service layer calls these — no SQL in service.py.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import OTPRecord, UserProfile


# ═══════════════════════════════════════════════════════════════════════
# USER PROFILE
# ═══════════════════════════════════════════════════════════════════════

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[UserProfile]:
    result = await db.execute(
        select(UserProfile).where(UserProfile.email == email.lower().strip())
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[UserProfile]:
    result = await db.execute(
        select(UserProfile).where(UserProfile.id == uuid.UUID(user_id))
    )
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    email: str,
    name: Optional[str],
    password_hash: Optional[str],
    provider: str,
    picture: Optional[str] = None,
    is_verified: bool = False,
) -> UserProfile:
    user = UserProfile(
        email         = email.lower().strip(),
        name          = name,
        password_hash = password_hash,
        provider      = provider,
        picture       = picture,
        is_verified   = is_verified,
    )
    db.add(user)
    await db.flush()   # get PK without committing
    return user


async def mark_user_verified(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(
        update(UserProfile)
        .where(UserProfile.id == user_id)
        .values(is_verified=True, updated_at=datetime.now(timezone.utc))
    )


async def update_password(db: AsyncSession, user_id: uuid.UUID, new_hash: str) -> None:
    await db.execute(
        update(UserProfile)
        .where(UserProfile.id == user_id)
        .values(password_hash=new_hash, updated_at=datetime.now(timezone.utc))
    )


async def update_user_picture(
    db: AsyncSession, user_id: uuid.UUID, picture: str
) -> None:
    await db.execute(
        update(UserProfile)
        .where(UserProfile.id == user_id)
        .values(picture=picture, updated_at=datetime.now(timezone.utc))
    )


# ═══════════════════════════════════════════════════════════════════════
# OTP RECORDS
# ═══════════════════════════════════════════════════════════════════════

OTP_TTL_MINUTES = 10


async def create_otp(
    db: AsyncSession,
    user_id: uuid.UUID,
    otp_hash: str,
) -> OTPRecord:
    # Invalidate any existing active OTPs for this user
    await db.execute(
        update(OTPRecord)
        .where(OTPRecord.user_id == user_id, OTPRecord.is_used == False)
        .values(is_used=True)
    )

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MINUTES)
    record = OTPRecord(
        user_id    = user_id,
        otp_hash   = otp_hash,
        expires_at = expires_at,
        attempts   = 0,
        is_used    = False,
    )
    db.add(record)
    await db.flush()
    return record


async def get_active_otp(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> Optional[OTPRecord]:
    """Fetch the most recent unused, unexpired OTP for user."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(OTPRecord)
        .where(
            OTPRecord.user_id   == user_id,
            OTPRecord.is_used   == False,
            OTPRecord.expires_at > now,
        )
        .order_by(OTPRecord.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def increment_otp_attempts(db: AsyncSession, otp_id: uuid.UUID) -> int:
    """Increment attempt counter. Returns new attempt count."""
    result = await db.execute(
        select(OTPRecord).where(OTPRecord.id == otp_id)
    )
    record = result.scalar_one_or_none()
    if record:
        record.attempts += 1
        await db.flush()
        return record.attempts
    return 0


async def mark_otp_used(db: AsyncSession, otp_id: uuid.UUID) -> None:
    await db.execute(
        update(OTPRecord)
        .where(OTPRecord.id == otp_id)
        .values(is_used=True)
    )


async def delete_expired_otps(db: AsyncSession) -> int:
    """Cleanup job — call periodically or on startup."""
    result = await db.execute(
        delete(OTPRecord).where(OTPRecord.expires_at < datetime.now(timezone.utc))
    )
    return result.rowcount
