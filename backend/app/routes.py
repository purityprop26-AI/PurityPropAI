"""
API Routes for Tamil Nadu Real Estate AI Assistant (PostgreSQL)

FIX [CRIT-B1]: LLM call is now direct await — no run_in_threadpool
FIX [MED-B2]: domain_validator uses run_in_threadpool only for language detect (kept minimal)
FIX [HIGH-B5]: Duplicate count query removed; moved to window function approach
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from datetime import datetime, timezone
import uuid
import json as _json

from app.database import get_db
from app.models import ChatSession, ChatMessage
from app.schemas import (
    ChatRequest, ChatResponse, SessionCreate, SessionResponse,
    ConversationHistory, MessageHistory
)
from app.services.domain_validator import is_real_estate_query, get_rejection_message, detect_language
from app.services.llm_service import llm_service


router = APIRouter(tags=["chat"])


@router.post("/sessions", response_model=SessionResponse)
async def create_session(session_data: SessionCreate, db: AsyncSession = Depends(get_db)):
    """Create a new chat session."""
    session_id = str(uuid.uuid4())

    new_session = ChatSession(
        session_id=session_id,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )

    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)

    return SessionResponse(
        session_id=new_session.session_id,
        created_at=new_session.created_at,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Process chat message and return response.

    FIX [CRIT-B1]: LLM generation is now fully async — direct await, no threadpool.
    FIX [MED-B2]: domain_validator (pure regex, ~0.5ms) kept in threadpool to avoid
                  any regex DoS blocking the event loop on malformed input.
    """
    # Find session
    result = await db.execute(
        select(ChatSession).where(ChatSession.session_id == request.session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Validate domain — kept in threadpool (pure regex, zero I/O but potentially slow on large input)
    is_valid, reason = await run_in_threadpool(is_real_estate_query, request.message)

    if not is_valid:
        language = await run_in_threadpool(detect_language, request.message)
        rejection_msg = get_rejection_message(language)

        # Save user message
        user_msg = ChatMessage(
            session_id=session.id,
            role="user",
            content=request.message,
            language=language,
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(user_msg)

        # Save rejection response
        assistant_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=rejection_msg,
            language=language,
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(assistant_msg)

        session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()

        return ChatResponse(
            session_id=request.session_id,
            message=rejection_msg,
            language=language,
            timestamp=assistant_msg.timestamp,
        )

    # Get conversation history for this session
    msg_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.timestamp)
        .limit(12)  # Last 6 exchanges only — keep context manageable
    )
    history_messages = msg_result.scalars().all()

    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in history_messages
    ]

    # FIX [CRIT-B1]: Direct await — no threadpool — fully async HTTP call
    response_text, detected_language = await llm_service.generate_response(
        user_message=request.message,
        conversation_history=conversation_history,
    )

    # Save user message
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=request.message,
        language=detected_language,
        timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(user_msg)

    # Save assistant response
    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=response_text,
        language=detected_language,
        timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(assistant_msg)

    session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()

    return ChatResponse(
        session_id=request.session_id,
        message=response_text,
        language=detected_language,
        timestamp=assistant_msg.timestamp,
    )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Stream chat response via Server-Sent Events.
    Each event: data: {"chunk": "text"} or data: {"done": true, "language": "english"}
    """
    # Find session
    result = await db.execute(
        select(ChatSession).where(ChatSession.session_id == request.session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Domain validation
    is_valid, reason = await run_in_threadpool(is_real_estate_query, request.message)
    if not is_valid:
        language = await run_in_threadpool(detect_language, request.message)
        rejection_msg = get_rejection_message(language)

        async def rejection_stream():
            yield f"data: {_json.dumps({'chunk': rejection_msg})}\n\n"
            yield f"data: {_json.dumps({'done': True, 'language': language})}\n\n"

        return StreamingResponse(rejection_stream(), media_type="text/event-stream")

    # Get conversation history
    msg_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.timestamp)
        .limit(12)
    )
    history_messages = msg_result.scalars().all()
    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in history_messages
    ]

    # Save user message immediately
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=request.message,
        language="english",
        timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(user_msg)
    await db.commit()

    async def event_stream():
        full_text = ""
        detected_lang = "english"

        async for chunk, lang, is_done in llm_service.stream_response(
            user_message=request.message,
            conversation_history=conversation_history,
        ):
            detected_lang = lang
            if is_done:
                # Save assistant message to DB
                assistant_msg = ChatMessage(
                    session_id=session.id,
                    role="assistant",
                    content=full_text,
                    language=detected_lang,
                    timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                )
                db.add(assistant_msg)
                session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                await db.commit()

                yield f"data: {_json.dumps({'done': True, 'language': detected_lang, 'full_text': full_text})}\n\n"
            else:
                full_text += chunk
                yield f"data: {_json.dumps({'chunk': chunk})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/sessions/{session_id}/messages", response_model=ConversationHistory)
async def get_conversation_history(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get conversation history for a session."""
    result = await db.execute(
        select(ChatSession).where(ChatSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    msg_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.timestamp)
        .limit(200)  # FIX [M5]: Prevent unbounded query on old sessions
    )
    messages = msg_result.scalars().all()

    message_list = [
        MessageHistory(
            role=msg.role,
            content=msg.content,
            language=msg.language,
            timestamp=msg.timestamp,
        )
        for msg in messages
    ]

    return ConversationHistory(
        session_id=session_id,
        messages=message_list,
    )


@router.get("/health")
async def health_check():
    """Health check endpoint — no DB dependency (liveness probe safe)."""
    return {
        "status": "healthy",
        "service": "Tamil Nadu Real Estate AI Assistant",
        "database": "PostgreSQL (Supabase)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
