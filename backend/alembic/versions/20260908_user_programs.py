"""Add user program subscriptions.

Revision ID: 20260908_user_programs
Revises: 20260908_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "20260908_user_programs"
down_revision = "20260908_initial"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if "user_programs" not in sa.inspect(bind).get_table_names():
        op.create_table(
            "user_programs",
            sa.Column("user_id", sa.String(36), sa.ForeignKey("user_profiles.id"), primary_key=True),
            sa.Column("program_id", sa.String(36), sa.ForeignKey("programs.id"), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        )


def downgrade():
    bind = op.get_bind()
    if "user_programs" in sa.inspect(bind).get_table_names(): op.drop_table("user_programs")
