from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.models import Course, CourseOffering, Institution, UserProfile
from app.services.pae import add_offering_to_pae, get_or_create_pae


def test_pae_is_unique_per_user_and_academic_year_and_accepts_manual_courses():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        institution = Institution(slug="ulb", name="ULB", schedule_provider="timeedit")
        user = UserProfile(auth_user_id="supabase-user")
        db.add_all([institution, user]); db.flush()
        course = Course(institution_id=institution.id, code="ELECH550", name="Embedded System Security", credits=5)
        db.add(course); db.flush()
        offering = CourseOffering(course_id=course.id, academic_year="2026-2027", semester="Q1")
        db.add(offering); db.flush()
        first = get_or_create_pae(db, user.id, "2026-2027")
        second = get_or_create_pae(db, user.id, "2026-2027")
        add_offering_to_pae(db, user.id, "2026-2027", offering.id)
        db.commit()
        assert first.id == second.id
        assert first.academic_year == "2026-2027"
        assert len(first.name) > 0
