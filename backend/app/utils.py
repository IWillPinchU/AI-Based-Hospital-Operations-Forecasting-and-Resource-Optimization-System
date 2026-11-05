from datetime import datetime, timezone
from typing import Any, Optional


def to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensures a datetime object is timezone-aware and normalized to UTC.

    - If dt is naive, assigns tzinfo=timezone.utc.
    - If dt is timezone-aware, converts it to UTC using astimezone(timezone.utc).
    - If dt is None, returns None.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def ensure_utc_validator(v: Any) -> Any:
    """Reusable Pydantic field validator for datetime fields requiring UTC."""
    if isinstance(v, datetime):
        return to_utc(v)
    return v
