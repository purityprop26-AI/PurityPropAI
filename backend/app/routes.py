"""
API Routes for Tamil Nadu Real Estate AI Assistant
"""

from fastapi import APIRouter, Depends, HTTPException
from odmantic import AIOEngine
from datetime import datetime
import uuid

from app.database import get_engine
from app.models import ChatSession, ChatMessage
from app.schemas import (
    ChatRequest, ChatResponse, SessionCreate, SessionResponse,
    ConversationHistory, MessageHistory
)
from app.services.domain_validator import is_real_estate_query, get_rejection_message, detect_language
from app.services.llm_service import llm_service


router = APIRouter(tags=["chat"])


@router.post("/sessions", response_model=SessionResponse)
async def create_session(session_data: SessionCreate, engine: AIOEngine = Depends(get_engine)):
    """Create a new chat session."""
    session_id = str(uuid.uuid4())
    
    new_session = ChatSession(
        session_id=session_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    await engine.save(new_session)
    
    return SessionResponse(
        session_id=new_session.session_id,
        created_at=new_session.created_at
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, engine: AIOEngine = Depends(get_engine)):
    """
    Process chat message and return response.
    """
    # Verify session exists
    session = await engine.find_one(ChatSession, ChatSession.session_id == request.session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Validate domain (real estate only)
    # Validate domain (real estate only)
    # Run CPU-bound validation in threadpool to enforce non-blocking behavior
    from fastapi.concurrency import run_in_threadpool
    
    is_valid, reason = await run_in_threadpool(is_real_estate_query, request.message)
    
    if not is_valid:
        # Detect language for rejection message
        language = await run_in_threadpool(detect_language, request.message)
        rejection_msg = get_rejection_message(language)
        
        # Save user message
        user_msg = ChatMessage(
            role="user",
            content=request.message,
            language=language,
            timestamp=datetime.utcnow()
        )
        session.messages.append(user_msg)
        
        # Save rejection response
        assistant_msg = ChatMessage(
            role="assistant",
            content=rejection_msg,
            language=language,
            timestamp=datetime.utcnow()
        )
        session.messages.append(assistant_msg)
        session.updated_at = datetime.utcnow()
        await engine.save(session)
        
        return ChatResponse(
            session_id=request.session_id,
            message=rejection_msg,
            language=language,
            timestamp=assistant_msg.timestamp
        )
    
    # Get conversation history from session
    history_messages = session.messages
    
    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in history_messages
    ]
    
    # Generate response using LLM
    # Generate response using LLM (Async Safe)
    from fastapi.concurrency import run_in_threadpool
    
    response_text, detected_language = await run_in_threadpool(
        llm_service.generate_response,
        user_message=request.message,
        conversation_history=conversation_history
    )
    
    # Save user message
    user_msg = ChatMessage(
        role="user",
        content=request.message,
        language=detected_language,
        timestamp=datetime.utcnow()
    )
    session.messages.append(user_msg)
    
    # Save assistant response
    assistant_msg = ChatMessage(
        role="assistant",
        content=response_text,
        language=detected_language,
        timestamp=datetime.utcnow()
    )
    session.messages.append(assistant_msg)
    
    # Update session timestamp
    session.updated_at = datetime.utcnow()
    
    await engine.save(session)
    
    return ChatResponse(
        session_id=request.session_id,
        message=response_text,
        language=detected_language,
        timestamp=assistant_msg.timestamp
    )


@router.get("/sessions/{session_id}/messages", response_model=ConversationHistory)
async def get_conversation_history(session_id: str, engine: AIOEngine = Depends(get_engine)):
    """Get conversation history for a session."""
    session = await engine.find_one(ChatSession, ChatSession.session_id == session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = session.messages
    
    message_list = [
        MessageHistory(
            role=msg.role,
            content=msg.content,
            language=msg.language,
            timestamp=msg.timestamp
        )
        for msg in messages
    ]
    
    return ConversationHistory(
        session_id=session_id,
        messages=message_list
    )


@router.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Tamil Nadu Real Estate AI Assistant",
        "timestamp": datetime.utcnow().isoformat()
    } 
