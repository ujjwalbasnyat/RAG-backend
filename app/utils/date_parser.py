from datetime import datetime

import dateparser

from app.core.logging import logger


def parse_date(value: str | None) -> str | None:
    """
    Parse natural language date string into YYYY-MM-DD format.
    Returns None if:
        - value is empty/None
        - dateparser cannot parse it
        - parsed date is in the past
    """
    if not value or not value.strip():
        return None

    parsed = dateparser.parse(
        value,
        settings={
            "PREFER_DATES_FROM": "future",
            "RETURN_AS_TIMEZONE_AWARE": False,
        },
    )

    if not parsed:
        logger.warning("date_parse_failed", raw_value=value)
        return None

    if parsed.date() < datetime.now().date():
        logger.warning("date_in_past", raw_value=value, parsed=str(parsed.date()))
        return None  # caller will ask user for a future date

    return parsed.strftime("%Y-%m-%d")