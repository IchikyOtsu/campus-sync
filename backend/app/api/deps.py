from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.models import UserProfile

security = HTTPBearer()

@lru_cache
def jwks_client(url: str): return PyJWKClient(f"{url}/auth/v1/.well-known/jwks.json")

def current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> UserProfile:
    settings = get_settings()
    if not settings.supabase_url: raise HTTPException(503, "Supabase Auth is not configured")
    try:
        key = jwks_client(settings.supabase_url).get_signing_key_from_jwt(credentials.credentials)
        claims = jwt.decode(credentials.credentials, key.key, algorithms=[key.algorithm_name], audience=settings.supabase_jwt_audience)
    except Exception as exc: raise HTTPException(401, "Invalid Supabase access token") from exc
    profile = db.scalar(select(UserProfile).where(UserProfile.auth_user_id == claims["sub"]))
    if not profile:
        profile = UserProfile(auth_user_id=claims["sub"], display_name=claims.get("user_metadata", {}).get("full_name")); db.add(profile); db.commit(); db.refresh(profile)
    return profile
