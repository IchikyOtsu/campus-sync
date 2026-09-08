from app.db.seed import seed
from app.db.session import Base, SessionLocal, engine
from app.models import models  # noqa: F401

Base.metadata.create_all(engine)
with SessionLocal() as session: seed(session)
