from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.user_programs import detail
from app.db.session import Base
from app.models.models import (
    Course,
    CourseOffering,
    Institution,
    Program,
    ProgramCourse,
    UserCourse,
    UserProfile,
    UserProgram,
)


def test_user_program_and_existing_hyphenated_ulb_course_is_added():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        ulb = Institution(slug="ulb", name="ULB", schedule_provider="timeedit")
        user = UserProfile(auth_user_id="supabase-user")
        db.add_all([ulb, user]); db.flush()
        provider_course = Course(institution_id=ulb.id, code="ELEC-H550", name="Embedded System Security", credits=5)
        followed_course = Course(institution_id=ulb.id, code="ELECH550", name="Embedded System Security", credits=5)
        db.add_all([provider_course, followed_course]); db.flush()
        program = Program(institution_id=ulb.id, code="M-SECUC", name="Master en cybersécurité", academic_year="2026-2027")
        db.add(program); db.flush()
        db.add(ProgramCourse(program_id=program.id, home_code="ELEC-H550", provider_course_id=provider_course.id, semester="Q1", required=True))
        offering = CourseOffering(course_id=followed_course.id, academic_year="2026-2027", semester=None)
        db.add(offering); db.flush()
        db.add_all([UserCourse(user_id=user.id, course_offering_id=offering.id), UserProgram(user_id=user.id, program_id=program.id)])
        db.commit(); db.refresh(program)
        # relationships are loaded by the endpoint query in production; attach for this unit-level status test.
        program.program_courses[0].provider_course = provider_course
        provider_course.institution = ulb
        response = detail(db, user, program)
        assert response["courses"][0]["home_code"] == "ELEC-H550"
        assert response["courses"][0]["user_status"] == "added"
        assert response["courses"][0]["connector_status"] == "available"
