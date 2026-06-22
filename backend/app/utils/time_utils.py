from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from app.config import settings


def get_tz() -> ZoneInfo:
    return ZoneInfo(settings.TIMEZONE)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def today_start_utc() -> datetime:
    """Start of calendar day in office timezone, returned as UTC."""
    tz = get_tz()
    local_now = datetime.now(tz)
    local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return local_start.astimezone(timezone.utc)


def local_date_to_utc_start(date_str: str) -> datetime:
    tz = get_tz()
    y, m, d = [int(x) for x in date_str.split("-")]
    local_start = datetime(y, m, d, 0, 0, 0, tzinfo=tz)
    return local_start.astimezone(timezone.utc)


def local_date_to_utc_end(date_str: str) -> datetime:
    tz = get_tz()
    y, m, d = [int(x) for x in date_str.split("-")]
    local_end = datetime(y, m, d, 23, 59, 59, tzinfo=tz)
    return local_end.astimezone(timezone.utc)


def to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def checkout_available_at(check_in: datetime) -> datetime:
    if check_in.tzinfo is None:
        check_in = check_in.replace(tzinfo=timezone.utc)
    return check_in + timedelta(minutes=settings.CHECKOUT_LOCKOUT_MINUTES)
