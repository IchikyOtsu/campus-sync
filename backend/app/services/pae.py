from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import UserPAE, UserPAECourse

DEFAULT_ACADEMIC_YEAR = "2026-2027"

def get_or_create_pae(db: Session, user_id: str, academic_year: str) -> UserPAE:
    pae = db.scalar(select(UserPAE).where(UserPAE.user_id == user_id, UserPAE.academic_year == academic_year))
    if pae:
        return pae
    pae = UserPAE(user_id=user_id, academic_year=academic_year, name=f"PAE {academic_year}")
    db.add(pae)
    db.flush()
    return pae

def add_offering_to_pae(db: Session, user_id: str, academic_year: str, offering_id: str, program_course_id: str | None = None) -> UserPAECourse:
    pae = get_or_create_pae(db, user_id, academic_year)
    item = db.get(UserPAECourse, {"user_pae_id": pae.id, "course_offering_id": offering_id})
    if item:
        if program_course_id and not item.program_course_id:
            item.program_course_id = program_course_id
        return item
    item = UserPAECourse(user_pae_id=pae.id, course_offering_id=offering_id, program_course_id=program_course_id)
    db.add(item)
    return item
