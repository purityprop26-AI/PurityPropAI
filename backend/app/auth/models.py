"""
Auth v2 — SQLAlchemy Models
Tables: user_profiles, otp_records
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

# Use existing Base from app.database
from app.database import Base


class UserProfile(Base):
    """
    Extended user profile table.
    Linked to Supabase auth user by email (source of truth = Supabase).
    Stores provider info and verification state managed by custom auth.
    """
    __tablename__ = "user_profiles"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email           = Column(String(255), unique=True, nullable=False, index=True)
    name            = Column(String(255), nullable=True)
    password_hash   = Column(Text, nullable=True)          # NULL for Google users
    provider        = Column(String(50), nullable=False, default="email")  # email | google
    picture         = Column(Text, nullable=True)
    is_verified     = Column(Boolean, nullable=False, default=False)
    created_at      = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at      = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                             onupdate=lambda: datetime.now(timezone.utc))

    otp_records = relationship("OTPRecord", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<UserProfile {self.email} [{self.provider}]>"


class OTPRecord(Base):
    """
    One-time password records for email verification.
    Raw OTP is NEVER stored — only SHA-256 hash.
    """
    __tablename__ = "otp_records"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    otp_hash    = Column(String(64), nullable=False)         # SHA-256 hex digest
    expires_at  = Column(DateTime(timezone=True), nullable=False)
    attempts    = Column(Integer, nullable=False, default=0)
    is_used     = Column(Boolean, nullable=False, default=False)
    created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("UserProfile", back_populates="otp_records")

    def __repr__(self):
        return f"<OTPRecord user={self.user_id} used={self.is_used}>"
