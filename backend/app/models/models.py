from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def uid() -> str: return str(uuid4())


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Institution(Timestamped, Base):
    __tablename__ = "institutions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    website_url: Mapped[str | None] = mapped_column(String(500))
    schedule_provider: Mapped[str] = mapped_column(String(80))


class Course(Timestamped, Base):
    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint("institution_id", "code", name="uq_course_institution_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id"))
    code: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(300))
    credits: Mapped[int | None] = mapped_column(Integer)
    institution: Mapped[Institution] = relationship()
    offerings: Mapped[list["CourseOffering"]] = relationship(back_populates="course")


class CourseOffering(Timestamped, Base):
    __tablename__ = "course_offerings"
    __table_args__ = (UniqueConstraint("course_id", "academic_year", "semester", name="uq_offering"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"))
    academic_year: Mapped[str] = mapped_column(String(20))
    semester: Mapped[str | None] = mapped_column(String(20))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    course: Mapped[Course] = relationship(back_populates="offerings")
    events: Mapped[list["ScheduleEvent"]] = relationship(back_populates="offering")


class ScheduleEvent(Timestamped, Base):
    __tablename__ = "schedule_events"
    __table_args__ = (UniqueConstraint("course_offering_id", "external_id", name="uq_event_source"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    course_offering_id: Mapped[str] = mapped_column(ForeignKey("course_offerings.id"))
    external_id: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(400))
    event_type: Mapped[str | None] = mapped_column(String(80))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    campus: Mapped[str | None] = mapped_column(String(160))
    building: Mapped[str | None] = mapped_column(String(160))
    room: Mapped[str | None] = mapped_column(String(160))
    reservation_info: Mapped[str | None] = mapped_column(Text)
    teacher: Mapped[str | None] = mapped_column(String(300))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    offering: Mapped[CourseOffering] = relationship(back_populates="events")


class Program(Base):
    __tablename__ = "programs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id"))
    code: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(300))
    academic_year: Mapped[str] = mapped_column(String(20))
    institution: Mapped[Institution] = relationship()
    program_courses: Mapped[list["ProgramCourse"]] = relationship(back_populates="program")


class ProgramCourse(Base):
    __tablename__ = "program_courses"
    __table_args__ = (UniqueConstraint("program_id", "home_code", name="uq_program_home_code"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    program_id: Mapped[str] = mapped_column(ForeignKey("programs.id"))
    home_code: Mapped[str] = mapped_column(String(80))
    provider_course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"))
    semester: Mapped[str | None] = mapped_column(String(20))
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    program: Mapped[Program] = relationship(back_populates="program_courses")
    provider_course: Mapped[Course] = relationship()


class UserProfile(Base):
    __tablename__ = "user_profiles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    auth_user_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(160))
    timezone: Mapped[str] = mapped_column(String(80), default="Europe/Brussels")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserPAE(Timestamped, Base):
    __tablename__ = "user_paes"
    __table_args__ = (UniqueConstraint("user_id", "academic_year", name="uq_user_pae_year"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"), index=True)
    academic_year: Mapped[str] = mapped_column(String(20))
    name: Mapped[str | None] = mapped_column(String(160))


class UserPAECourse(Base):
    __tablename__ = "user_pae_courses"
    __table_args__ = (UniqueConstraint("user_pae_id", "course_offering_id", name="uq_pae_offering"),)
    user_pae_id: Mapped[str] = mapped_column(ForeignKey("user_paes.id"), primary_key=True)
    course_offering_id: Mapped[str] = mapped_column(ForeignKey("course_offerings.id"), primary_key=True)
    program_course_id: Mapped[str | None] = mapped_column(ForeignKey("program_courses.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ScheduleChange(Base):
    __tablename__ = "schedule_changes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey("schedule_events.id"))
    change_type: Mapped[str] = mapped_column(String(80))
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class UserProgram(Base):
    __tablename__ = "user_programs"
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.id"), primary_key=True)
    program_id: Mapped[str] = mapped_column(ForeignKey("programs.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
