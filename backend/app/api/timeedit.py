from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import current_user
from app.connectors.timeedit import TimeEditConnector, TimeEditUnavailable
from app.db.session import get_db
from app.models.models import Course, CourseOffering, Institution, UserPAECourse, UserProfile
from app.services.pae import add_offering_to_pae, pae_summary
from app.services.sync import sync_events

router = APIRouter(prefix="/api/institutions/ulb", tags=["timeedit"])


class CourseSelection(BaseModel):
    code: str
    external_id: str
    academic_year: str


def serialize(candidate, institution: str | None = None):
    return {"institution": institution or candidate.institution, "code": candidate.code, "name": candidate.name, "external_id": candidate.external_id, "academic_year": candidate.academic_year, "object_type": candidate.object_type}


@router.get("/courses/search")
async def search_ulb_courses(
    q: str = Query(min_length=1, max_length=100),
    academic_year: str = Query(pattern=r"^20\d{2}-20\d{2}$"),
    user: UserProfile = Depends(current_user),
):
    del user
    try:
        return [serialize(item) for item in await TimeEditConnector().search_courses(q, academic_year)]
    except (TimeEditUnavailable, ValueError) as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/courses/add")
async def add_ulb_course(
    selection: CourseSelection,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(current_user),
):
    connector = TimeEditConnector()
    try:
        candidates = await connector.search_courses(selection.code, selection.academic_year)
    except (TimeEditUnavailable, ValueError) as exc:
        raise HTTPException(503, str(exc)) from exc
    canonical = lambda code: "".join(char for char in code.casefold() if char.isalnum())
    match = next((item for item in candidates if item.external_id == selection.external_id and canonical(item.code) == canonical(selection.code)), None)
    if not match:
        raise HTTPException(422, "The selected course is no longer available from ULB TimeEdit")
    try:
        events = await connector.get_course_events(match.external_id, selection.academic_year)
    except TimeEditUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    teaching_events = [event for event in events if event.title.strip() and not event.title.startswith("Info:") and event.end_at > event.start_at]
    if not teaching_events:
        raise HTTPException(422, "TimeEdit returned no teaching events for this course and academic year")
    detected_institution = connector.institution_from_events(teaching_events, match.institution)
    institution_slug = "he2b" if detected_institution == "esi" else detected_institution
    institution = db.scalar(select(Institution).where(Institution.slug == institution_slug))
    if not institution:
        raise HTTPException(503, f"Institution {detected_institution} is not seeded")
    canonical = lambda code: "".join(char for char in code.casefold() if char.isalnum())
    course = next((item for item in db.scalars(select(Course).where(Course.institution_id == institution.id)) if canonical(item.code) == canonical(match.code)), None)
    if not course:
        course = Course(institution_id=institution.id, code=match.code, name=match.name, credits=None)
        db.add(course); db.flush()
    offering = next((item for item in db.scalars(select(CourseOffering).join(CourseOffering.course).where(CourseOffering.academic_year == selection.academic_year, Course.institution_id == institution.id).options(joinedload(CourseOffering.course))) if canonical(item.course.code) == canonical(match.code)), None)
    if not offering:
        offering = CourseOffering(course_id=course.id, academic_year=selection.academic_year, semester=None, external_id=match.external_id, source_url=connector.provider.base_url)
        db.add(offering); db.flush()
    else:
        offering.external_id = match.external_id
    result = sync_events(db, offering, teaching_events)
    existing_pae = pae_summary(db, user.id, selection.academic_year)
    linked_courses = db.execute(select(UserPAECourse, Course).join(CourseOffering, CourseOffering.id == UserPAECourse.course_offering_id).join(Course, Course.id == CourseOffering.course_id).where(UserPAECourse.user_pae_id == existing_pae["id"])).all()
    matching_links = [link for link, linked_course in linked_courses if canonical(linked_course.code) == canonical(match.code)]
    already_in_pae = bool(matching_links)
    for link in matching_links:
        if link.course_offering_id != offering.id:
            db.delete(link)
    add_offering_to_pae(db, user.id, selection.academic_year, offering.id)
    db.commit()
    return {"offering_id": offering.id, "course": serialize(match, detected_institution), "sync": result, "already_in_pae": already_in_pae, "pae": pae_summary(db, user.id, selection.academic_year), "offering": {"id": offering.id, "academic_year": offering.academic_year, "semester": offering.semester, "course": {"id": course.id, "code": course.code, "name": course.name, "credits": course.credits, "institution": {"slug": institution.slug, "name": institution.name, "provider": institution.schedule_provider}}}}
