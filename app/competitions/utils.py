from datetime import datetime, timedelta, timezone
from typing import Optional
import pytz

TR_TZ = pytz.timezone("Europe/Istanbul")

def now_tr() -> datetime:
    return datetime.now(TR_TZ)

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def end_of_month_utc(year: int, month: int) -> datetime:
    if month == 12:
        return datetime(year + 1, 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
    return datetime(year, month + 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)

def is_registration_period_tr(now: Optional[datetime] = None) -> bool:
    now = now or now_tr()
    return now.day >= 25