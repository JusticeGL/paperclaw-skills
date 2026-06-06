from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Window:
    start: date
    end: date
    tz: str

    @property
    def padded_start(self) -> date:
        return self.start - timedelta(days=1)

    @property
    def padded_end(self) -> date:
        return self.end + timedelta(days=1)

    def contains(self, value: date) -> bool:
        return self.start <= value <= self.end

    def to_dict(self) -> dict[str, str]:
        return {"start": self.start.isoformat(), "end": self.end.isoformat(), "tz": self.tz}


def compute_window(tz_name: str = "Asia/Shanghai", window_days: int = 7, today: date | None = None) -> Window:
    if today is None:
        today = datetime.now(ZoneInfo(tz_name)).date()
    end = today
    start = end - timedelta(days=window_days)
    return Window(start=start, end=end, tz=tz_name)


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        pass
    for fmt in ("%Y %b %d", "%Y %b", "%Y"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.date()
        except ValueError:
            continue
    return None


def to_local_date(value: str | date | datetime | None, tz_name: str = "Asia/Shanghai") -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            normalized = text.replace("Z", "+00:00")
            dt = datetime.fromisoformat(normalized)
        except ValueError:
            return parse_date(text)
    if dt.tzinfo is None:
        return dt.date()
    return dt.astimezone(ZoneInfo(tz_name)).date()


def utc_date(value: date) -> str:
    return datetime(value.year, value.month, value.day, tzinfo=timezone.utc).date().isoformat()
