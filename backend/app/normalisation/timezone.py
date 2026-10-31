"""
Timezone normalisation for multi-bank cross-border reconciliation.
Converts any bank local timestamp to UTC while preserving original metadata.
"""

from datetime import datetime, timezone
import zoneinfo
from typing import Tuple


def normalise_to_utc(dt: datetime, source_tz_name: str = "Asia/Kolkata") -> Tuple[datetime, datetime]:
    """
    Converts a datetime to UTC.
    Returns (utc_datetime, original_datetime).
    """
    if dt.tzinfo is None:
        try:
            source_tz = zoneinfo.ZoneInfo(source_tz_name)
            localized_dt = dt.replace(tzinfo=source_tz)
        except Exception:
            # Fallback to IST if unknown
            source_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
            localized_dt = dt.replace(tzinfo=source_tz)
    else:
        localized_dt = dt

    utc_dt = localized_dt.astimezone(timezone.utc).replace(tzinfo=None)
    return utc_dt, localized_dt
