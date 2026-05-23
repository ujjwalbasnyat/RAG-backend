import json

from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.logging import logger
from app.db.redis import redis_client as _redis

_settings = get_settings()


async def add_message(session_id: str, role: str, content: str) -> None:
    key = f"chat:{session_id}"
    try:
        payload = json.dumps({"role": role, "content": content})
        await _redis.rpush(key, payload)
        await _redis.ltrim(key, -_settings.chat_memory_limit, -1)
        await _redis.expire(key, _settings.chat_memory_ttl)
    except Exception as exc:
        logger.error("redis_chat_write_failed", error=str(exc))


async def get_history(session_id: str) -> list[dict[str, str]]:
    key = f"chat:{session_id}"
    try:
        entries = await _redis.lrange(key, -_settings.chat_memory_limit * 2, -1)
        history: list[dict[str, str]] = []
        for entry in entries:
            try:
                item = json.loads(entry)
                if "role" in item and "content" in item:
                    history.append({"role": item["role"], "content": item["content"]})
            except Exception:
                continue
        return history
    except Exception as exc:
        logger.error("redis_chat_read_failed", error=str(exc))
        return []


async def clear_chat(session_id: str) -> None:
    key = f"chat:{session_id}"
    try:
        await _redis.delete(key)
    except Exception as exc:
        logger.error("redis_chat_clear_failed", error=str(exc))
