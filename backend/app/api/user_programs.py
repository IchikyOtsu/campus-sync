from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import current_user
from app.connectors.timeedit import TimeEditConnector, TimeEditUnavailable
from app.db.session import get_db
from app.models.models import (
    Course,
    CourseOffering,
    Program,
    ProgramCourse,
    UserPAE,
    UserPAECourse,
    UserProfile,
    UserProgram,
)
from app.services.pae import add_offering_to_pae
from app.services.sync import sync_events

router = APIRouter(prefix="/api/me/programs", tags=["user-programs"])


def canonical(code: str) -> str:
    return "".join(char for char in code.casefold() if char.isalnum())


def program_summary(program: Program):
    return {"id": program.id, "code": program.code, "name": program.name, "academic_year": program.academic_year, "institution": program.institution.slug}


def detail(db: Session, user: UserProfile, program: Program):
    offerings = db.scalars(
        select(CourseOffering)
        .join(UserPAECourse, UserPAECourse.course_offering_id == CourseOffering.id)
        .join(UserPAE, UserPAE.id == UserPAECourse.user_pae_id)
        .join(CourseOffering.course)
        .options(joinedload(CourseOffering.course).joinedload(Course.institution))
        .where(UserPAE.user_id == user.id, UserPAE.academic_year == program.academic_year, CourseOffering.academic_year == program.academic_year)
    ).unique()
    followed = {(item.course.institution.slug, canonical(item.course.code)) for item in offerings}
    courses = []
    for item in sorted(program.program_courses, key=lambda row: row.home_code):
        provider = item.provider_course.institution
        is_added = (provider.slug, canonical(item.provider_course.code)) in followed
        connector_status = "available" if provider.slug == "ulb" else "not_implemented"
        courses.append({
            "id": item.id, "home_code": item.home_code, "provider": provider.slug,
            "provider_code": item.provider_course.code, "name": item.provider_course.name,
            "semester": item.semester, "required": item.required,
            "connector_status": connector_status,
            "user_status": "added" if is_added else ("available" if connector_status == "available" else "not_added"),
        })
    return {**program_summary(program), "courses": courses}


def get_program(db: Session, program_id: str) -> Program:
    program = db.scalar(select(Program).where(Program.id == program_id).options(joinedload(Program.institution), joinedload(Program.program_courses).joinedload(ProgramCourse.provider_course).joinedload(Course.institution)))
    if not program: raise HTTPException(404, "Program not found")
    return program


@router.get("")
def my_programs(db: Session = Depends(get_db), user: UserProfile = Depends(current_user)):
    rows = db.scalars(select(Program).join(UserProgram).where(UserProgram.user_id == user.id).options(joinedload(Program.institution)))
    return [program_summary(program) for program in rows]


@router.post("/{program_id}")
def add_program(program_id: str, db: Session = Depends(get_db), user: UserProfile = Depends(current_user)):
    program = get_program(db, program_id)
    if not db.get(UserProgram, {"user_id": user.id, "program_id": program.id}):
        db.add(UserProgram(user_id=user.id, program_id=program.id)); db.commit()
    return detail(db, user, program)


@router.delete("/{program_id}", status_code=204)
def remove_program(program_id: str, db: Session = Depends(get_db), user: UserProfile = Depends(current_user)):
    item = db.get(UserProgram, {"user_id": user.id, "program_id": program_id})
    if item: db.delete(item); db.commit()


@router.get("/{program_id}")
def my_program(program_id: str, db: Session = Depends(get_db), user: UserProfile = Depends(current_user)):
    if not db.get(UserProgram, {"user_id": user.id, "program_id": program_id}): raise HTTPException(404, "Program is not assigned to this user")
    return detail(db, user, get_program(db, program_id))


@router.post("/{program_id}/courses/{program_course_id}/add")
async def add_program_course(program_id: str, program_course_id: str, db: Session = Depends(get_db), user: UserProfile = Depends(current_user)):
    if not db.get(UserProgram, {"user_id": user.id, "program_id": program_id}):
        raise HTTPException(404, "Program is not assigned to this user")
    item = db.scalar(select(ProgramCourse).where(ProgramCourse.id == program_course_id, ProgramCourse.program_id == program_id).options(joinedload(ProgramCourse.provider_course).joinedload(Course.institution)))
    if not item: raise HTTPException(404, "Program course not found")
    if item.provider_course.institution.slug != "ulb":
        raise HTTPException(409, "This provider connector is not implemented yet")
    connector = TimeEditConnector()
    try:
        candidates = await connector.search_courses(item.provider_course.code, get_program(db, program_id).academic_year)
        match = next((candidate for candidate in candidates if canonical(candidate.code) == canonical(item.provider_course.code)), None)
        if not match: raise HTTPException(422, "Course not found in ULB TimeEdit")
        events = await connector.get_course_events(match.external_id, get_program(db, program_id).academic_year)
    except TimeEditUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    teaching = [event for event in events if event.title.strip() and not event.title.startswith("Info:") and event.end_at > event.start_at]
    if not teaching: raise HTTPException(422, "TimeEdit returned no teaching events")
    provider = item.provider_course.institution
    offerings = db.scalars(select(CourseOffering).join(CourseOffering.course).where(CourseOffering.academic_year == get_program(db, program_id).academic_year, Course.institution_id == provider.id).options(joinedload(CourseOffering.course)))
    offering = next((candidate for candidate in offerings if canonical(candidate.course.code) == canonical(match.code)), None)
    if not offering:
        course = item.provider_course
        offering = CourseOffering(course_id=course.id, academic_year=get_program(db, program_id).academic_year, semester=None, external_id=match.external_id, source_url=connector.provider.base_url)
        db.add(offering); db.flush()
    offering.external_id = match.external_id
    result = sync_events(db, offering, teaching)
    add_offering_to_pae(db, user.id, get_program(db, program_id).academic_year, offering.id, item.id)
    db.commit()
    return {"offering_id": offering.id, "sync": result}
