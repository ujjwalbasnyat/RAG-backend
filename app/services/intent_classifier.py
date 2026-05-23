from groq import AsyncGroq

from app.core.config import get_settings
from app.core.logging import logger

from app.services.intent_classification_prompt import INTENT_CLASSIFICATION_PROMPT

_settings = get_settings()
_client = AsyncGroq(api_key=_settings.groq_api_key)

_INTENTS = {"BOOK_INTERVIEW", "BOOKING_CANCEL", "GENERAL_QUERY"}


async def classify_intent(message: str) -> str:
    """Classify user intent using LLM; fallback to heuristics on failure."""
    if not _settings.groq_api_key:
        return _heuristic_intent(message)


    try:
        response = await _client.chat.completions.create(
            model=_settings.groq_chat_model,
            messages=[
                {"role": "system", "content": INTENT_CLASSIFICATION_PROMPT},
                {"role": "user", "content": message},
            ],
        )
        label = response.choices[0].message.content.strip().split()[0].upper()
        logger.info("intent_classified", raw=response.choices[0].message.content.strip(), label=label)
        if label in _INTENTS:
            return label
        return _heuristic_intent(message)
    except Exception as exc:
        logger.error("intent_classify_failed", error=str(exc))
        return _heuristic_intent(message)


def _heuristic_intent(message: str) -> str:
    text = message.lower()
    if any(w in text for w in ["cancel", "stop", "forget", "never mind"]):
        return "BOOKING_CANCEL"
    if any(w in text for w in ["book an interview", "schedule interview", "set up interview", "book appointment"]):
        return "BOOK_INTERVIEW"
    return "GENERAL_QUERY"
