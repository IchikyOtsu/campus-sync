from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.base import NormalizedEvent
from app.models.models import CourseOffering, ScheduleChange, ScheduleEvent


def sync_events(db: Session, offering: CourseOffering, events: list[NormalizedEvent]) -> dict[str, int]:
    existing = {event.external_id: event for event in db.scalars(select(ScheduleEvent).where(ScheduleEvent.course_offering_id == offering.id))}
    received = set(); created = changed = removed = 0
    fields = ("title", "event_type", "start_at", "end_at", "campus", "building", "room", "teacher", "source_url", "source_updated_at")
    for incoming in events:
        received.add(incoming.external_id); event = existing.get(incoming.external_id)
        if not event:
            db.add(ScheduleEvent(course_offering_id=offering.id, **incoming.__dict__)); created += 1; continue
        for field in fields:
            old, new = getattr(event, field), getattr(incoming, field)
            if old != new:
                db.add(ScheduleChange(event_id=event.id, change_type=field, old_value=str(old), new_value=str(new)))
                setattr(event, field, new); changed += 1
        event.is_cancelled = False
    for external_id, event in existing.items():
        if external_id not in received and not event.is_cancelled:
            event.is_cancelled = True; db.add(ScheduleChange(event_id=event.id, change_type="cancelled", old_value="active", new_value="cancelled")); removed += 1
    offering.last_synced_at = datetime.now(UTC); db.commit()
    return {"created": created, "changed": changed, "removed": removed}
