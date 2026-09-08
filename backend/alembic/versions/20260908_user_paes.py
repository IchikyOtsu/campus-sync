"""Replace global user courses with academic-year PAE courses.

Revision ID: 20260908_user_paes
Revises: 20260908_user_programs
"""
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "20260908_user_paes"
down_revision = "20260908_user_programs"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "user_paes" not in tables:
        op.create_table(
            "user_paes",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("user_profiles.id"), nullable=False, index=True),
            sa.Column("academic_year", sa.String(20), nullable=False),
            sa.Column("name", sa.String(160)),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.UniqueConstraint("user_id", "academic_year", name="uq_user_pae_year"),
        )
    if "user_pae_courses" not in tables:
        op.create_table(
            "user_pae_courses",
            sa.Column("user_pae_id", sa.String(36), sa.ForeignKey("user_paes.id"), primary_key=True),
            sa.Column("course_offering_id", sa.String(36), sa.ForeignKey("course_offerings.id"), primary_key=True),
            sa.Column("program_course_id", sa.String(36), sa.ForeignKey("program_courses.id")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.UniqueConstraint("user_pae_id", "course_offering_id", name="uq_pae_offering"),
        )
    if not {"user_courses", "course_offerings"}.issubset(tables):
        return
    rows = bind.execute(sa.text("""
        SELECT uc.user_id, uc.course_offering_id, co.academic_year
        FROM user_courses uc JOIN course_offerings co ON co.id = uc.course_offering_id
    """)).mappings()
    paes: dict[tuple[str, str], str] = {}
    for row in rows:
        key = (row["user_id"], row["academic_year"])
        pae_id = paes.get(key)
        if not pae_id:
            existing = bind.execute(sa.text("SELECT id FROM user_paes WHERE user_id = :user_id AND academic_year = :academic_year"), {"user_id": key[0], "academic_year": key[1]}).scalar()
            pae_id = existing or str(uuid4())
            if not existing:
                bind.execute(sa.text("INSERT INTO user_paes (id, user_id, academic_year, name) VALUES (:id, :user_id, :academic_year, :name)"), {"id": pae_id, "user_id": key[0], "academic_year": key[1], "name": f"PAE {key[1]}"})
            paes[key] = pae_id
        bind.execute(sa.text("""
            INSERT INTO user_pae_courses (user_pae_id, course_offering_id)
            VALUES (CAST(:pae_id AS varchar(36)), CAST(:offering_id AS varchar(36)))
            ON CONFLICT (user_pae_id, course_offering_id) DO NOTHING
        """), {"pae_id": pae_id, "offering_id": row["course_offering_id"]})


def downgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "user_pae_courses" in tables:
        op.drop_table("user_pae_courses")
    if "user_paes" in tables:
        op.drop_table("user_paes")
