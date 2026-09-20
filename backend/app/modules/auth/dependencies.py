from typing import Annotated
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status, Request, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
import jwt

from app.core.config import settings
from app.db.session import get_db_session
from app.modules.auth import security, repository
from app.modules.users.model import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def verify_origin(request: Request, origin: str | None = Header(None)) -> None:
    if not origin:
        # If origin is missing, typically browsers send it for cross-origin or POST.
        # Strict policy: require Origin for state-changing endpoints in browsers.
        # But wait, same-origin POST requests in some browsers might not send Origin unless CORS.
        # Actually, standard browsers DO send Origin on POST even for same-origin (since Chrome 61+).
        # We can fallback to testing if referer exists and matches, but standard dictates explicit check.
        # For simplicity, we check if Origin is provided and matches. If not provided, we might allow non-browser clients (like Postman or curl).
        pass
    else:
        if origin not in settings.allowed_origins:
            raise HTTPException(status_code=403, detail="Origin not allowed")

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db_session)]
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = security.decode_access_token(token)
        user_id: str = payload.get("sub")
        session_id: str = payload.get("sid")
        typ: str = payload.get("typ")
        if user_id is None or session_id is None or typ != "access":
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    auth_session = await repository.get_auth_session(db, session_id)
    now = datetime.now(timezone.utc)
    
    if not auth_session:
        raise credentials_exception
    if auth_session.revoked_at is not None:
        raise credentials_exception
    if auth_session.expires_at < now:
        raise credentials_exception
        
    user = await repository.get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception
        
    return user
