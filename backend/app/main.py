from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes import router
from app.api.timeedit import router as timeedit_router
from app.api.user_programs import router as user_programs_router
from app.core.config import get_settings
from app.db.session import engine

settings = get_settings()
app = FastAPI(title="campus-sync API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(","), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)
app.include_router(timeedit_router)
app.include_router(user_programs_router)

@app.get("/health")
def health():
    try:
        with engine.connect() as connection: connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}
    except Exception:
        return {"status": "degraded", "database": "unavailable"}
