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


def parse_query_datetime(val: Optional[str]) -> Optional[datetime]:
    """Parses query string datetime, handling ISO-8601, 'Z', and URL '+' space decoding."""
    if not val:
        return None
    val = val.strip()
    if " " in val:
        parts = val.split(" ")
        if len(parts) == 2 and ":" in parts[1] and len(parts[1]) <= 6:
            val = f"{parts[0]}+{parts[1]}"
    if val.endswith("Z"):
        val = val[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(val)
        return to_utc(dt)
    except Exception as e:
        raise ValueError(f"Invalid datetime format '{val}'. Expected ISO format.") from e

