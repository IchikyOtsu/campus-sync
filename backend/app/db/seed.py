from sqlalchemy import select

from app.models.models import Course, CourseOffering, Institution, Program, ProgramCourse

SEED_COURSES = [
    ("ELEC-H550", "ulb", "ELEC-H550", "Embedded System Security"), ("MATH-F307", "ulb", "MATH-F307", "Mathématiques discrètes"),
    ("INFO-Y024", "uclouvain", "LINFO2145", "Cloud Computing"), ("INFO-Y030", "uclouvain", "LDACS1310", "Introduction to Applied Cryptography"),
    ("INFO-Y112", "unamur", "ICYBM101", "Machine Learning and Data Mining"), ("INFO-Y115", "he2b", "5SEC1A", "Secure Software Design and Web Security"),
]

def seed(db):
    institutions = {}
    for slug, name, provider in [("ulb", "Université libre de Bruxelles", "timeedit_planned"), ("uclouvain", "UCLouvain", "ade_planned"), ("unamur", "UNamur", "ade_planned"), ("he2b", "HE2B / ESI", "custom_planned")]:
        item = db.scalar(select(Institution).where(Institution.slug == slug))
        if not item: item = Institution(slug=slug, name=name, schedule_provider=provider); db.add(item); db.flush()
        institutions[slug] = item
    program = db.scalar(select(Program).where(Program.code == "M-SECUC", Program.academic_year == "2026-2027"))
    if not program: program = Program(institution_id=institutions["ulb"].id, code="M-SECUC", name="Master en cybersécurité", academic_year="2026-2027"); db.add(program); db.flush()
    for home_code, provider_slug, code, name in SEED_COURSES:
        course = db.scalar(select(Course).where(Course.institution_id == institutions[provider_slug].id, Course.code == code))
        if not course: course = Course(institution_id=institutions[provider_slug].id, code=code, name=name, credits=5); db.add(course); db.flush()
        offering = db.scalar(select(CourseOffering).where(CourseOffering.course_id == course.id, CourseOffering.academic_year == "2026-2027", CourseOffering.semester == "Q1"))
        if not offering: db.add(CourseOffering(course_id=course.id, academic_year="2026-2027", semester="Q1"))
        if not db.scalar(select(ProgramCourse).where(ProgramCourse.program_id == program.id, ProgramCourse.home_code == home_code)): db.add(ProgramCourse(program_id=program.id, home_code=home_code, provider_course_id=course.id, semester="Q1", required=True))
    db.commit()
