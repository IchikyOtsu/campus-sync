from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from dateutil.rrule import rrulestr
from icalendar import Calendar

from app.connectors.base import NormalizedEvent, ScheduleConnector


class IcalConnector(ScheduleConnector):
    """Generic, read-only ICS connector. Recurrences are expanded for a bounded window."""
    def __init__(self, source: str | bytes, source_url: str | None = None, timezone: str = "Europe/Brussels"):
        self.source, self.source_url, self.tz = source, source_url, ZoneInfo(timezone)

    async def _content(self) -> bytes:
        if isinstance(self.source, bytes): return self.source
        if self.source.startswith(("https://", "http://")):
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                response = await client.get(self.source)
                response.raise_for_status()
                return response.content
        return self.source.encode()

    @staticmethod
    def _datetime(value, tz: ZoneInfo) -> datetime:
        value = getattr(value, "dt", value)
        if not isinstance(value, datetime): value = datetime.combine(value, datetime.min.time())
        return value.replace(tzinfo=tz) if value.tzinfo is None else value

    @staticmethod
    def _description_fields(component) -> tuple[str | None, str | None]:
        description = str(component.get("DESCRIPTION", "")).replace("\n", "\n")
        lines = [line.strip() for line in description.splitlines() if line.strip()]
        details = [line for line in lines[1:] if not line.upper().startswith("ID ")]
        reservation_info = " ".join(details).lstrip(": ") or None
        summary = str(component.get("SUMMARY", ""))
        teacher_match = __import__("re").search(r"Enseignant:\s*([^,]+)", summary, __import__("re").IGNORECASE)
        return reservation_info, teacher_match.group(1).strip() if teacher_match else None

    async def search_courses(self, query: str): return []
    async def get_course(self, external_id: str): return None

    async def get_events(self, external_id: str = "calendar") -> list[NormalizedEvent]:
        calendar = Calendar.from_ical(await self._content())
        result: list[NormalizedEvent] = []
        for component in calendar.walk("VEVENT"):
            if not component.get("DTSTART"): continue
            start = self._datetime(component.decoded("DTSTART"), self.tz)
            end = self._datetime(component.decoded("DTEND"), self.tz) if component.get("DTEND") else start
            uid = str(component.get("UID", f"ics-{start.isoformat()}"))
            reservation_info, teacher = self._description_fields(component)
            occurrences = [(uid, start, end)]
            if component.get("RRULE"):
                rule = rrulestr(component.get("RRULE").to_ical().decode(), dtstart=start)
                horizon = start.replace(year=start.year + 1)
                occurrences = [(f"{uid}:{item.isoformat()}", item, item + (end - start)) for item in rule.between(start, horizon, inc=True)]
            for event_id, event_start, event_end in occurrences:
                result.append(NormalizedEvent(
                    external_id=event_id, title=str(component.get("SUMMARY", "Untitled event")),
                    start_at=event_start, end_at=event_end, room=str(component.get("LOCATION", "")) or None,
                    event_type=str(component.get("CATEGORIES", "")) or None,
                    reservation_info=reservation_info, teacher=teacher, source_url=self.source_url,
                    source_updated_at=self._datetime(component.decoded("LAST-MODIFIED"), self.tz) if component.get("LAST-MODIFIED") else None,
                ))
        return result
