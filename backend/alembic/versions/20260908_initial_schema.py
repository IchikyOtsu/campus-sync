"""Initial campus-sync relational schema.

Revision ID: 20260908_initial
"""
from alembic import op
from app.db.session import Base
from app.models import models  # noqa: F401

revision = "20260908_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    Base.metadata.create_all(bind=op.get_bind())

def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())
