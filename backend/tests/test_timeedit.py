import asyncio

import httpx
import pytest

from app.connectors.base import NormalizedEvent
from app.connectors.timeedit import TimeEditConnector, TimeEditUnavailable

HTML = '''<div class="searchObject" data-id="181733.5" data-name="CHIMF415, Electrochimie, 202627"></div>
<div class="searchObject" data-id="156292.5" data-name="CHIMF415, Electrochimie, 202526"></div>'''


def client(body: str, status: int = 200):
    return httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(status, text=body)))


def test_timeedit_search():
    async def run():
        async with client(HTML) as transport:
            result = await TimeEditConnector(client=transport).search_courses("CHIMF415", "2026-2027")
        assert [(item.code, item.external_id, item.academic_year) for item in result] == [("CHIMF415", "181733.5", "2026-2027")]
    asyncio.run(run())


def test_timeedit_parse():
    parsed = TimeEditConnector._parse_results(HTML, "2026-2027")
    assert parsed[0].name == "Electrochimie"


def test_timeedit_course_not_found():
    async def run():
        async with client('<div class="emptysearch">Aucun résultats</div>') as transport:
            assert await TimeEditConnector(client=transport).search_courses("ELEC-H550", "2026-2027") == []
    asyncio.run(run())


def test_timeedit_unavailable():
    async def run():
        async with client("unavailable", 503) as transport:
            with pytest.raises(TimeEditUnavailable): await TimeEditConnector(client=transport).search_courses("ELEC", "2026-2027")
    asyncio.run(run())


def test_timeedit_events(monkeypatch):
    event = NormalizedEvent("event-1", "Course", __import__('datetime').datetime(2026, 9, 1), __import__('datetime').datetime(2026, 9, 1, 2))
    async def events(*args, **kwargs): return [event]
    monkeypatch.setattr("app.connectors.timeedit.IcalConnector.get_events", events)
    assert asyncio.run(TimeEditConnector().get_course_events("181733.5", "2026-2027"))[0].external_id == "event-1"


def test_timeedit_sync_idempotent():
    from datetime import UTC, datetime

    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from app.db.session import Base
    from app.models.models import Course, CourseOffering, Institution, ScheduleEvent
    from app.services.sync import sync_events

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        institution = Institution(slug="ulb-test", name="ULB test", schedule_provider="timeedit")
        db.add(institution); db.flush()
        course = Course(institution_id=institution.id, code="TEST-1", name="Test", credits=None)
        db.add(course); db.flush()
        offering = CourseOffering(course_id=course.id, academic_year="2026-2027", semester=None)
        db.add(offering); db.commit(); db.refresh(offering)
        event = NormalizedEvent("te-uid-1", "Test session", datetime(2026, 9, 1, 10, tzinfo=UTC), datetime(2026, 9, 1, 12, tzinfo=UTC))
        assert sync_events(db, offering, [event])["created"] == 1
        assert sync_events(db, offering, [event])["created"] == 0
        assert len(list(db.scalars(select(ScheduleEvent)))) == 1


def test_timeedit_search_strips_administrative_hyphen():
    requested = []
    async def run():
        def handler(request):
            requested.append(str(request.url))
            return httpx.Response(200, text=HTML)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as transport:
            await TimeEditConnector(client=transport).search_courses("ELEC-H550", "2026-2027")
    asyncio.run(run())
    assert "search_text=ELECH550" in requested[0]
