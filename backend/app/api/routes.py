from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import current_user
from app.connectors.ical import IcalConnector
from app.db.session import get_db
from app.models.models import (
    Course,
    CourseOffering,
    Institution,
    Program,
    ProgramCourse,
    ScheduleEvent,
    UserCourse,
    UserProfile,
)
from app.services.conflicts import user_conflicts
from app.services.sync import sync_events

router = APIRouter(prefix="/api")

def offering_data(offering: CourseOffering, home_code: str | None = None):
    c = offering.course
    return {"id": offering.id, "academic_year": offering.academic_year, "semester": offering.semester, "last_synced_at": offering.last_synced_at, "course": {"id": c.id, "code": c.code, "home_code": home_code, "name": c.name, "credits": c.credits, "institution": {"slug": c.institution.slug, "name": c.institution.name, "provider": c.institution.schedule_provider}}}

@router.get("/me")
def me(user: UserProfile = Depends(current_user)): return {"id": user.id, "display_name": user.display_name, "timezone": user.timezone}

@router.get("/institutions")
def institutions(db: Session = Depends(get_db)):
    return [{"slug": item.slug, "name": item.name, "schedule_provider": item.schedule_provider} for item in db.scalars(select(Institution).order_by(Institution.name))]

@router.get("/courses")
def courses(query: str = "", institution: str | None = None, db: Session = Depends(get_db)):
    statement = select(Course).options(joinedload(Course.institution)).where(Course.code.ilike(f"%{query}%") | Course.name.ilike(f"%{query}%"))
    if institution: statement = statement.join(Course.institution).where(Institution.slug == institution)
    return [{"id": item.id, "code": item.code, "name": item.name, "credits": item.credits, "institution": item.institution.slug} for item in db.scalars(statement)]

@router.get("/me/courses")
def my_courses(db: Session = Depends(get_db), user: UserProfile = Depends(current_user)):
    statement = select(CourseOffering).join(UserCourse).where(UserCourse.user_id == user.id).options(joinedload(CourseOffering.course).joinedload(Course.institution))
    return [offering_data(item) for item in db.scalars(statement).unique()]

@router.post("/me/courses/{offering_id}")
def add_course(offering_id: str, db: Session = Depends(get_db), user: UserProfile = Depends(current_user)):
    if not db.get(CourseOffering, offering_id): raise HTTPException(404, "Offering not found")
    if not db.get(UserCourse, {"user_id": user.id, "course_offering_id": offering_id}): db.add(UserCourse(user_id=user.id, course_offering_id=offering_id)); db.commit()
    return {"ok": True}

@router.delete("/me/courses/{offering_id}", status_code=204)
def remove_course(offering_id: str, db: Session = Depends(get_db), user: UserProfile = Depends(current_user)):
    item = db.get(UserCourse, {"user_id": user.id, "course_offering_id": offering_id})
    if item: db.delete(item); db.commit()

@router.get("/me/events")
def my_events(start: datetime | None = None, end: datetime | None = None, db: Session = Depends(get_db), user: UserProfile = Depends(current_user)):
    statement = select(ScheduleEvent).join(ScheduleEvent.offering).join(UserCourse).where(UserCourse.user_id == user.id, ScheduleEvent.is_cancelled.is_(False)).options(joinedload(ScheduleEvent.offering).joinedload(CourseOffering.course).joinedload(Course.institution))
    if start: statement = statement.where(ScheduleEvent.end_at > start)
    if end: statement = statement.where(ScheduleEvent.start_at < end)
    return [{"id": e.id, "external_id": e.external_id, "title": e.title, "event_type": e.event_type, "start_at": e.start_at, "end_at": e.end_at, "campus": e.campus, "building": e.building, "room": e.room, "teacher": e.teacher, "source_url": e.source_url, "course": {"code": e.offering.course.code, "name": e.offering.course.name, "institution": e.offering.course.institution.name}} for e in db.scalars(statement).unique()]

@router.get("/me/conflicts")
def conflicts(db: Session = Depends(get_db), user: UserProfile = Depends(current_user)):
    return [{"start_at": item["start_at"], "end_at": item["end_at"], "duration_minutes": item["minutes"], "courses": [{"code": item["first"].offering.course.code, "institution": item["first"].offering.course.institution.name}, {"code": item["second"].offering.course.code, "institution": item["second"].offering.course.institution.name}]} for item in user_conflicts(db, user.id)]

@router.get("/programs")
def programs(db: Session = Depends(get_db)):
    return [{"id": p.id, "code": p.code, "name": p.name, "academic_year": p.academic_year, "institution": p.institution.slug} for p in db.scalars(select(Program).options(joinedload(Program.institution)))]

@router.get("/programs/{program_id}")
def program(program_id: str, db: Session = Depends(get_db)):
    p = db.scalar(select(Program).where(Program.id == program_id).options(joinedload(Program.program_courses).joinedload(ProgramCourse.provider_course).joinedload(Course.institution)))
    if not p: raise HTTPException(404, "Program not found")
    return {"id": p.id, "code": p.code, "name": p.name, "academic_year": p.academic_year, "courses": [{"home_code": pc.home_code, "semester": pc.semester, "required": pc.required, "course": {"id": pc.provider_course.id, "code": pc.provider_course.code, "name": pc.provider_course.name, "institution": pc.provider_course.institution.slug}} for pc in p.program_courses]}

@router.post("/programs/{program_id}/add")
def add_program(program_id: str, db: Session = Depends(get_db), user: UserProfile = Depends(current_user)):
    p = db.scalar(select(Program).where(Program.id == program_id).options(joinedload(Program.program_courses).joinedload(ProgramCourse.provider_course).joinedload(Course.offerings)))
    if not p: raise HTTPException(404, "Program not found")
    count = 0
    for item in p.program_courses:
        offering = next((x for x in item.provider_course.offerings if x.academic_year == p.academic_year and x.semester == item.semester), None)
        if offering and not db.get(UserCourse, {"user_id": user.id, "course_offering_id": offering.id}): db.add(UserCourse(user_id=user.id, course_offering_id=offering.id)); count += 1
    db.commit(); return {"added": count}

class IcsUrl(BaseModel): url: HttpUrl

async def _import_ics(data: bytes, label: str, source_url: str | None, db: Session, user: UserProfile):
    ics = db.scalar(select(Institution).where(Institution.slug == "ics"))
    if not ics: ics = Institution(slug="ics", name="Calendrier iCalendar", schedule_provider="ical"); db.add(ics); db.flush()
    course = Course(institution_id=ics.id, code=f"ICS-{label[:20]}", name=label, credits=None); db.add(course); db.flush()
    offering = CourseOffering(course_id=course.id, academic_year="imported", semester=None, source_url=source_url, external_id=source_url); db.add(offering); db.flush()
    result = sync_events(db, offering, await IcalConnector(data, source_url).get_events())
    if not db.get(UserCourse, {"user_id": user.id, "course_offering_id": offering.id}): db.add(UserCourse(user_id=user.id, course_offering_id=offering.id)); db.commit()
    return {"offering_id": offering.id, **result}

@router.post("/me/imports/ics-file")
async def import_ics_file(file: UploadFile = File(...), db: Session = Depends(get_db), user: UserProfile = Depends(current_user)):
    if not file.filename or not file.filename.lower().endswith(".ics"): raise HTTPException(400, "An .ics file is required")
    return await _import_ics(await file.read(), file.filename.removesuffix(".ics"), None, db, user)

@router.post("/me/imports/ics-url")
async def import_ics_url(payload: IcsUrl, db: Session = Depends(get_db), user: UserProfile = Depends(current_user)):
    connector = IcalConnector(str(payload.url), str(payload.url)); data = await connector._content()
    return await _import_ics(data, "Imported calendar", str(payload.url), db, user)
