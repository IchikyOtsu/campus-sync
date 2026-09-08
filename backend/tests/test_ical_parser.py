import asyncio

from app.connectors.ical import IcalConnector

ICS = b"""BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:test-1\nDTSTART;TZID=Europe/Brussels:20260923T103000\nDTEND;TZID=Europe/Brussels:20260923T123000\nSUMMARY:Cloud Computing\nLOCATION:SUD 08\nEND:VEVENT\nEND:VCALENDAR"""

def test_ical_parser_keeps_brussels_timezone():
    event = asyncio.run(IcalConnector(ICS).get_events())[0]
    assert event.external_id == "test-1" and event.room == "SUD 08"
    assert str(event.start_at.tzinfo) == "Europe/Brussels"
