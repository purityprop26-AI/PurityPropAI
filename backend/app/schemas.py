from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List



class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    session_id: str = Field(..., description="Unique session identifier")
    message: str = Field(..., min_length=1, description="User message")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    session_id: str
    message: str
    language: str
    timestamp: datetime
    
    class Config:
        from_attributes = True


class SessionCreate(BaseModel):
    """Request model for creating a new session."""
    pass


class SessionResponse(BaseModel):
    """Response model for session creation."""
    session_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class MessageHistory(BaseModel):
    """Model for message in history."""
    role: str
    content: str
    language: Optional[str]
    timestamp: datetime
    
    class Config:
        from_attributes = True


class ConversationHistory(BaseModel):
    """Response model for conversation history."""
    session_id: str
    messages: List[MessageHistory]


# Authentication Schemas (Supabase Auth)
# Only UserResponse remains — Supabase handles registration/login directly

class UserResponse(BaseModel):
    """Response model for user data (from Supabase Auth)."""
    id: str
    email: str
    name: str
    created_at: str

    class Config:
        from_attributes = True

