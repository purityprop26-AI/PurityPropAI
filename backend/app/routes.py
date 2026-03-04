"""
API Routes for Tamil Nadu Real Estate AI Assistant (PostgreSQL)

Per-user chat sessions — each user's chats are isolated via owner_id.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func, delete
from datetime import datetime, timezone
import uuid
import json as _json

from app.database import get_db
from app.models import ChatSession, ChatMessage
from app.schemas import (
    ChatRequest, ChatResponse, SessionCreate, SessionResponse,
    ConversationHistory, MessageHistory,
    SessionListItem, SessionListResponse, SessionRenameRequest,
)
from app.services.domain_validator import is_real_estate_query, get_rejection_message, detect_language
from app.services.llm_service import llm_service

# ── Auth dependency ────────────────────────────────────────────────────
from app.auth.security import decode_access_token, extract_bearer


router = APIRouter(tags=["chat"])


async def get_current_user_optional(request: Request) -> dict | None:
    """Extract JWT if present. Returns payload or None (for anonymous)."""
    token = extract_bearer(request.headers.get("authorization", ""))
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    try:
        from main import token_blocklist
        jti = payload.get("jti")
        if jti and token_blocklist.is_blocked(jti):
            return None
    except Exception:
        pass
    return payload


async def require_auth(request: Request) -> dict:
    """Require valid JWT. Raises 401 if missing/invalid."""
    user = await get_current_user_optional(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# ─────────────────────────────────────────────────────────────────────────
# SESSION CRUD — Per-User Chat Management
# ─────────────────────────────────────────────────────────────────────────

@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """List all chat sessions for the authenticated user, newest first."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token.")

    msg_count_sq = (
        select(
            ChatMessage.session_id,
            sa_func.count(ChatMessage.id).label("msg_count"),
        )
        .group_by(ChatMessage.session_id)
        .subquery()
    )

    result = await db.execute(
        select(
            ChatSession.session_id,
            ChatSession.title,
            ChatSession.created_at,
            ChatSession.updated_at,
            sa_func.coalesce(msg_count_sq.c.msg_count, 0).label("message_count"),
        )
        .outerjoin(msg_count_sq, ChatSession.id == msg_count_sq.c.session_id)
        .where(ChatSession.owner_id == user_id)
        .order_by(ChatSession.updated_at.desc())
        .limit(50)
    )
    rows = result.all()

    sessions = [
        SessionListItem(
            session_id=r.session_id,
            title=r.title or "New Chat",
            created_at=r.created_at,
            updated_at=r.updated_at,
            message_count=r.message_count,
        )
        for r in rows
    ]

    return SessionListResponse(sessions=sessions, total=len(sessions))


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a new chat session. Links to user if authenticated."""
    session_id = str(uuid.uuid4())

    user = await get_current_user_optional(request)
    owner_id = user.get("sub") if user else None

    new_session = ChatSession(
        session_id=session_id,
        owner_id=owner_id,
        title=(session_data.title or "New Chat")[:120],
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )

    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)

    return SessionResponse(
        session_id=new_session.session_id,
        title=new_session.title,
        created_at=new_session.created_at,
    )


@router.patch("/sessions/{session_id}")
async def rename_session(
    session_id: str,
    body: SessionRenameRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Rename a chat session (ownership validated)."""
    user_id = current_user.get("sub")

    result = await db.execute(
        select(ChatSession).where(
            ChatSession.session_id == session_id,
            ChatSession.owner_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    session.title = body.title[:120]
    session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()

    return {"ok": True, "session_id": session_id, "title": session.title}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Delete a chat session and all its messages (ownership validated)."""
    user_id = current_user.get("sub")

    result = await db.execute(
        select(ChatSession).where(
            ChatSession.session_id == session_id,
            ChatSession.owner_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    await db.delete(session)
    await db.commit()

    return {"ok": True, "deleted": session_id}


@router.delete("/sessions")
async def clear_all_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Delete ALL chat sessions for the authenticated user."""
    user_id = current_user.get("sub")

    result = await db.execute(
        select(ChatSession.id).where(ChatSession.owner_id == user_id)
    )
    session_ids = [r[0] for r in result.all()]

    if session_ids:
        await db.execute(
            delete(ChatMessage).where(ChatMessage.session_id.in_(session_ids))
        )
        await db.execute(
            delete(ChatSession).where(ChatSession.owner_id == user_id)
        )
        await db.commit()

    return {"ok": True, "deleted_count": len(session_ids)}


# ─────────────────────────────────────────────────────────────────────────
# CHAT — Message Processing
# ─────────────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Process chat message and return response."""
    result = await db.execute(
        select(ChatSession).where(ChatSession.session_id == request.session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    is_valid, reason = await run_in_threadpool(is_real_estate_query, request.message)

    if not is_valid:
        language = await run_in_threadpool(detect_language, request.message)
        rejection_msg = get_rejection_message(language)

        user_msg = ChatMessage(
            session_id=session.id, role="user", content=request.message,
            language=language, timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(user_msg)

        assistant_msg = ChatMessage(
            session_id=session.id, role="assistant", content=rejection_msg,
            language=language, timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(assistant_msg)

        session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        if session.title == "New Chat":
            session.title = request.message[:80]
        await db.commit()

        return ChatResponse(
            session_id=request.session_id, message=rejection_msg,
            language=language, timestamp=assistant_msg.timestamp,
        )

    # Conversation history
    msg_result = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.timestamp).limit(12)
    )
    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in msg_result.scalars().all()
    ]

    response_text, detected_language = await llm_service.generate_response(
        user_message=request.message,
        conversation_history=conversation_history,
    )

    user_msg = ChatMessage(
        session_id=session.id, role="user", content=request.message,
        language=detected_language, timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(user_msg)

    assistant_msg = ChatMessage(
        session_id=session.id, role="assistant", content=response_text,
        language=detected_language, timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(assistant_msg)

    session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if session.title == "New Chat":
        session.title = request.message[:80]
    await db.commit()

    return ChatResponse(
        session_id=request.session_id, message=response_text,
        language=detected_language, timestamp=assistant_msg.timestamp,
    )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Stream chat response via Server-Sent Events."""
    result = await db.execute(
        select(ChatSession).where(ChatSession.session_id == request.session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    is_valid, reason = await run_in_threadpool(is_real_estate_query, request.message)
    if not is_valid:
        language = await run_in_threadpool(detect_language, request.message)
        rejection_msg = get_rejection_message(language)

        async def rejection_stream():
            yield f"data: {_json.dumps({'chunk': rejection_msg})}\n\n"
            yield f"data: {_json.dumps({'done': True, 'language': language})}\n\n"

        return StreamingResponse(rejection_stream(), media_type="text/event-stream")

    msg_result = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.timestamp).limit(12)
    )
    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in msg_result.scalars().all()
    ]

    user_msg = ChatMessage(
        session_id=session.id, role="user", content=request.message,
        language="english", timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(user_msg)
    if session.title == "New Chat":
        session.title = request.message[:80]
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
                assistant_msg = ChatMessage(
                    session_id=session.id, role="assistant", content=full_text,
                    language=detected_lang, timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
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
        select(ChatMessage).where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.timestamp).limit(200)
    )

    return ConversationHistory(
        session_id=session_id,
        messages=[
            MessageHistory(
                role=msg.role, content=msg.content,
                language=msg.language, timestamp=msg.timestamp,
            )
            for msg in msg_result.scalars().all()
        ],
    )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Tamil Nadu Real Estate AI Assistant",
        "database": "PostgreSQL (Supabase)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
