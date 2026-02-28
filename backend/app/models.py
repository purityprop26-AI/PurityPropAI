"""
Database Models for Tamil Nadu Real Estate AI Assistant (PostgreSQL/SQLAlchemy)
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    """User table."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationship to chat sessions
    sessions = relationship("ChatSession", back_populates="user", lazy="selectin")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, name={self.name})>"


class ChatSession(Base):
    """Chat session table."""
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions", lazy="selectin")
    messages = relationship("ChatMessage", back_populates="session", order_by="ChatMessage.timestamp", lazy="selectin")

    def __repr__(self):
        return f"<ChatSession(id={self.id}, session_id={self.session_id})>"


class ChatMessage(Base):
    """Chat message table — each message is a separate row."""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    language = Column(String(20), nullable=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationship back to session
    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, role={self.role})>"
