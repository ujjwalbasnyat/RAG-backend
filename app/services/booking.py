import json
import re
from dataclasses import dataclass

from groq import AsyncGroq
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BookingError
from app.core.logging import logger
from app.models.sql import InterviewBooking
from app.utils.date_parser import parse_date
from app.services.booking_prompt import BOOKING_EXTRACTION_PROMPT
from app.db.redis import redis_client as _redis

_settings = get_settings()
_client = AsyncGroq(api_key=_settings.groq_api_key)


@dataclass
class BookingState:
    name: str | None = None
    email: str | None = None
    date: str | None = None
    time: str | None = None

    @property
    def complete(self) -> bool:
        return all([self.name, self.email, self.date, self.time])

    def missing_fields(self) -> list[str]:
        missing = []
        if not self.name:
            missing.append("name")
        if not self.email:
            missing.append("email")
        if not self.date:
            missing.append("date")
        if not self.time:
            missing.append("time")
        return missing


async def handle_booking_message(
    session_id: str,
    message: str,
    db_session: AsyncSession,
) -> tuple[str, BookingState]:
    state = await get_booking_state(session_id)
    extracted = await _extract_slots(message)

    if extracted.name and not state.name:
        state.name = extracted.name
    if extracted.email and not state.email:
        state.email = extracted.email
    if extracted.date and not state.date:
        state.date = extracted.date
    if extracted.time and not state.time:
        state.time = extracted.time

    if state.complete:
        booking = InterviewBooking(
            session_id=session_id,
            name=state.name or "",
            email=state.email or "",
            date=state.date or "",
            time=state.time or "",
        )
        try:
            db_session.add(booking)
            await db_session.commit()
        except Exception as exc:
            await db_session.rollback()
            logger.error("booking_persist_failed", error=str(exc))
            raise BookingError("Failed to save booking") from exc
        await clear_booking_state(session_id)
        return ("Your interview is booked. I have saved your details.", state)

    await set_booking_state(session_id, state)
    missing = ", ".join(state.missing_fields())
    return (f"Please provide your {missing} to book the interview.", state)


async def cancel_booking(session_id: str) -> str:
    await clear_booking_state(session_id)
    return "Your booking request has been canceled."


async def get_booking_state(session_id: str) -> BookingState:
    key = f"booking:{session_id}"
    try:
        raw = await _redis.get(key)
        if not raw:
            return BookingState()
        data = json.loads(raw)
        return BookingState(
            name=data.get("name"),
            email=data.get("email"),
            date=data.get("date"),
            time=data.get("time"),
        )
    except Exception as exc:
        logger.error("redis_booking_read_failed", error=str(exc))
        return BookingState()


async def set_booking_state(session_id: str, state: BookingState) -> None:
    key = f"booking:{session_id}"
    try:
        payload = json.dumps(
            {
                "name": state.name,
                "email": state.email,
                "date": state.date,
                "time": state.time,
            }
        )
        await _redis.set(key, payload, ex=_settings.booking_ttl)
    except Exception as exc:
        logger.error("redis_booking_write_failed", error=str(exc))


async def clear_booking_state(session_id: str) -> None:
    key = f"booking:{session_id}"
    try:
        await _redis.delete(key)
    except Exception as exc:
        logger.error("redis_booking_clear_failed", error=str(exc))


async def _extract_slots(message: str) -> BookingState:
    if not _settings.groq_api_key:
        return _heuristic_extract(message)


    try:
        response = await _client.chat.completions.create(
            model=_settings.groq_chat_model,
            messages=[
                {"role": "system", "content": BOOKING_EXTRACTION_PROMPT},
                {"role": "user", "content": message},
            ],
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
        return BookingState(
            name=_clean_text(data.get("name")),
            email=_validate_email(data.get("email")),
            date=parse_date(_clean_text(data.get("date"))),
            time=_clean_text(data.get("time")),
        )
    except Exception as exc:
        logger.error("booking_extract_failed", error=str(exc))
        return _heuristic_extract(message)


def _heuristic_extract(message: str) -> BookingState:
    email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", message)
    email = email_match.group(0) if email_match else None
    name = None
    name_match = re.search(r"my name is ([A-Za-z ]+)", message, re.IGNORECASE)
    if name_match:
        name = name_match.group(1).strip()
    return BookingState(
        name=name,
        email=_validate_email(email),
        date=parse_date(message),
        time=None,
    )


def _clean_text(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    return value if value else None


def _validate_email(value: str | None) -> str | None:
    if not value:
        return None
    if re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", value):
        return value
    return None
