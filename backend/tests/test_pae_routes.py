from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import current_user
from app.connectors.base import NormalizedEvent
from app.connectors.timeedit import TimeEditCourse
from app.db.session import Base, get_db
from app.main import app
from app.models.models import Course, CourseOffering, Institution, UserPAECourse, UserProfile
from app.services.pae import add_offering_to_pae


def test_pae_routes_return_a_committed_manual_offering():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with Session(engine) as db:
        institution = Institution(slug="ulb", name="ULB", schedule_provider="timeedit")
        user = UserProfile(auth_user_id="test-user")
        db.add_all([institution, user]); db.flush()
        course = Course(institution_id=institution.id, code="ELECH550", name="Embedded System Security", credits=5)
        db.add(course); db.flush()
        offering = CourseOffering(course_id=course.id, academic_year="2026-2027", semester="Q1")
        db.add(offering); db.flush()
        add_offering_to_pae(db, user.id, "2026-2027", offering.id)
        db.commit()
        user_id, offering_id = user.id, offering.id

    def override_db():
        with factory() as db:
            yield db

    def override_user():
        with factory() as db:
            return db.get(UserProfile, user_id)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = override_user
    try:
        client = TestClient(app)
        pae = client.get("/api/me/pae?academic_year=2026-2027")
        courses = client.get("/api/me/pae/courses?academic_year=2026-2027")
    finally:
        app.dependency_overrides.clear()

    assert pae.status_code == 200
    assert pae.json()["academic_year"] == "2026-2027"
    assert pae.json()["course_count"] == 1
    assert courses.status_code == 200
    assert [item["id"] for item in courses.json()] == [offering_id]
    assert courses.json()[0]["course"]["code"] == "ELECH550"
    with Session(engine) as db:
        assert db.scalar(select(UserPAECourse).where(UserPAECourse.course_offering_id == offering_id)) is not None


def test_timeedit_add_commits_course_to_pae_and_returns_summary(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with Session(engine) as db:
        institution = Institution(slug="ulb", name="ULB", schedule_provider="timeedit")
        user = UserProfile(auth_user_id="timeedit-user")
        db.add_all([institution, user]); db.commit()
        user_id = user.id

    async def search_courses(_self, _query, academic_year):
        return [TimeEditCourse("178081.5", "ELECH550", "Embedded System Security", academic_year)]

    async def course_events(_self, _external_id, _academic_year):
        return [NormalizedEvent("event-1", "Embedded System Security", datetime(2026, 9, 1, 10, tzinfo=UTC), datetime(2026, 9, 1, 12, tzinfo=UTC))]

    def override_db():
        with factory() as db:
            yield db

    def override_user():
        with factory() as db:
            return db.get(UserProfile, user_id)

    monkeypatch.setattr("app.api.timeedit.TimeEditConnector.search_courses", search_courses)
    monkeypatch.setattr("app.api.timeedit.TimeEditConnector.get_course_events", course_events)
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = override_user
    try:
        response = TestClient(app).post("/api/institutions/ulb/courses/add", json={"code": "ELECH550", "external_id": "178081.5", "academic_year": "2026-2027"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["pae"]["academic_year"] == "2026-2027"
    assert response.json()["pae"]["course_count"] == 1
    with Session(engine) as db:
        offering = db.scalar(select(CourseOffering).join(Course).where(Course.code == "ELECH550"))
        assert offering is not None
        assert db.scalar(select(UserPAECourse).where(UserPAECourse.course_offering_id == offering.id)) is not None
