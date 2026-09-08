from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.models import Course, CourseOffering, ScheduleEvent, UserCourse


def user_conflicts(db: Session, user_id: str, start: datetime | None = None, end: datetime | None = None):
    query = select(ScheduleEvent).join(ScheduleEvent.offering).join(UserCourse, UserCourse.course_offering_id == ScheduleEvent.course_offering_id).where(UserCourse.user_id == user_id, ScheduleEvent.is_cancelled.is_(False)).options(joinedload(ScheduleEvent.offering).joinedload(CourseOffering.course).joinedload(Course.institution))
    if start: query = query.where(ScheduleEvent.end_at > start)
    if end: query = query.where(ScheduleEvent.start_at < end)
    events = sorted(db.scalars(query).unique(), key=lambda item: item.start_at)
    conflicts = []
    for index, first in enumerate(events):
        for second in events[index + 1:]:
            if second.start_at >= first.end_at: break
            overlap_start, overlap_end = max(first.start_at, second.start_at), min(first.end_at, second.end_at)
            if overlap_start < overlap_end:
                conflicts.append({"first": first, "second": second, "start_at": overlap_start, "end_at": overlap_end, "minutes": int((overlap_end - overlap_start).total_seconds() / 60)})
    return conflicts
