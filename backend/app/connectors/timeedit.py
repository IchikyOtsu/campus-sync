"""Public TimeEdit connector. No credentials or student account are used."""
import re
from dataclasses import dataclass
from html import unescape
from urllib.parse import urlencode

import httpx

from app.connectors.base import NormalizedEvent
from app.connectors.ical import IcalConnector


@dataclass(frozen=True)
class TimeEditProvider:
    slug: str
    base_url: str
    schedule_id: int = 10
    course_type: int = 5
    timezone: str = "Europe/Brussels"


ULB_TIMEEDIT = TimeEditProvider(
    slug="ulb", base_url="https://cloud.timeedit.net/be_ulb/web/public/"
)


@dataclass(frozen=True)
class TimeEditCourse:
    external_id: str
    code: str
    name: str
    academic_year: str
    institution: str = "unknown"
    object_type: str = "course"


class TimeEditUnavailable(RuntimeError): pass


class TimeEditConnector:
    def __init__(self, provider: TimeEditProvider = ULB_TIMEEDIT, client: httpx.AsyncClient | None = None):
        self.provider, self.client = provider, client

    @staticmethod
    def _year_token(academic_year: str) -> str:
        match = re.fullmatch(r"(20\d{2})-(20\d{2})", academic_year)
        if not match or int(match.group(2)) != int(match.group(1)) + 1:
            raise ValueError("academic_year must have the form 2026-2027")
        return match.group(1) + match.group(2)[-2:]

    @staticmethod
    def _institution_from_label(code: str, name: str) -> str:
        label = f"{code} {name}".casefold()
        if "uclouvain" in label or re.search(r"\bucl\b", label):
            return "uclouvain"
        if "unamur" in label or re.search(r"\buniversité de namur\b", label):
            return "unamur"
        if "he2b" in label or re.search(r"\besi\b", label):
            return "esi"
        return "ulb"

    @staticmethod
    def _parse_results(html: str, academic_year: str) -> list[TimeEditCourse]:
        candidates = re.findall(r'data-id="([^"]+)"[^>]*?data-name="([^"]+)"', html)
        target_year = TimeEditConnector._year_token(academic_year)
        results: list[TimeEditCourse] = []
        for external_id, raw_name in candidates:
            parts = [part.strip() for part in unescape(raw_name).split(",")]
            if len(parts) < 3 or parts[-1] != target_year:
                continue
            code, name = parts[0], ", ".join(parts[1:-1])
            institution = TimeEditConnector._institution_from_label(code, name)
            results.append(TimeEditCourse(external_id=external_id, code=code, name=name, academic_year=academic_year, institution=institution))
        return results

    async def search_courses(self, query: str, academic_year: str) -> list[TimeEditCourse]:
        query = query.strip()
        if not query: return []
        # TimeEdit ULB indexes mnemonic codes without their administrative hyphen.
        if re.fullmatch(r"[A-Za-z]+-[A-Za-z]*\d+", query): query = query.replace("-", "")
        params = {"max": 100, "fr": "t", "partajax": "t", "im": "f", "sid": self.provider.schedule_id, "l": "fr_SY", "search_text": query.strip(), "types": self.provider.course_type}
        url = f"{self.provider.base_url}objects.html?{urlencode(params)}"
        try:
            if self.client:
                response = await self.client.get(url)
            else:
                async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                    response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise TimeEditUnavailable("TimeEdit public is unavailable") from exc
        return self._parse_results(response.text, academic_year)

    async def get_course_events(self, external_course_id: str, academic_year: str) -> list[NormalizedEvent]:
        start_year = int(academic_year[:4]); end_year = start_year + 1
        params = {"sid": self.provider.schedule_id, "p": f"{start_year}0731.x,{end_year}0731.x", "objects": external_course_id}
        source_url = f"{self.provider.base_url}ri.ics?{urlencode(params)}"
        try:
            return await IcalConnector(source_url, source_url, self.provider.timezone).get_events()
        except (httpx.HTTPError, ValueError) as exc:
            raise TimeEditUnavailable("TimeEdit iCalendar export is unavailable or malformed") from exc
