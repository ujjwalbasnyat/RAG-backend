from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BookingError
from app.core.logging import logger
from app.db.session import get_db
from app.schemas.chat import BookingStatus, ChatQueryRequest, ChatQueryResponse, SourceChunk
from app.services.booking import cancel_booking, handle_booking_message
from app.services.chat_memory import add_message
from app.services.intent_classifier import classify_intent
from app.services.rag import answer_query

router = APIRouter()


@router.post("/chat/query", response_model=ChatQueryResponse)
async def chat_query(
    payload: ChatQueryRequest,
    session: AsyncSession = Depends(get_db),
) -> ChatQueryResponse:
    intent = await classify_intent(payload.query)

    if intent == "BOOKING_CANCEL":
        response_text = await cancel_booking(payload.session_id)
        await add_message(payload.session_id, "user", payload.query)
        await add_message(payload.session_id, "assistant", response_text)
        return ChatQueryResponse(
            response=response_text,
            intent=intent,
            sources=[],
            booking=None,
        )

    if intent == "BOOK_INTERVIEW":
        try:
            response_text, state = await handle_booking_message(
                payload.session_id,
                payload.query,
                session,
            )
        except BookingError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        await add_message(payload.session_id, "user", payload.query)
        await add_message(payload.session_id, "assistant", response_text)
        booking_status = BookingStatus(
            name=state.name,
            email=state.email,
            date=state.date,
            time=state.time,
            complete=state.complete,
        )
        return ChatQueryResponse(
            response=response_text,
            intent=intent,
            sources=[],
            booking=booking_status,
        )

    try:
        response_text, chunks = await answer_query(
            query=payload.query,
            session_id=payload.session_id,
            document_id=str(payload.document_id) if payload.document_id else None,
        )
    except Exception as exc:
        logger.error("chat_query_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Chat query failed") from exc

    await add_message(payload.session_id, "user", payload.query)
    await add_message(payload.session_id, "assistant", response_text)

    sources = [
        SourceChunk(
            document_id=chunk.document_id,
            filename=chunk.filename,
            chunk_index=chunk.chunk_index,
            score=chunk.score,
        )
        for chunk in chunks
    ]

    return ChatQueryResponse(
        response=response_text,
        intent=intent,
        sources=sources,
        booking=None,
    )
