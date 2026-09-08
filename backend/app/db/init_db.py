from sqlalchemy import inspect, text

from app.db.seed import seed
from app.db.session import Base, SessionLocal, engine
from app.models import models  # noqa: F401

EXPECTED_ALEMBIC_REVISION = "20260908_user_paes"


def require_schema_at_head():
    with engine.connect() as connection:
        tables = set(inspect(connection).get_table_names())
        if "alembic_version" not in tables:
            raise RuntimeError("Base non migrée : exécutez `alembic upgrade head` avant le démarrage.")
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
        if revision != EXPECTED_ALEMBIC_REVISION:
            raise RuntimeError(f"Base non migrée : révision {revision!r}, attendue {EXPECTED_ALEMBIC_REVISION!r}. Exécutez `alembic upgrade head`.")
        missing = {"user_paes", "user_pae_courses"} - tables
        if missing:
            raise RuntimeError(f"Schéma PAE incomplet : tables manquantes {sorted(missing)}.")


require_schema_at_head()
Base.metadata.create_all(engine)
with SessionLocal() as session: seed(session)
