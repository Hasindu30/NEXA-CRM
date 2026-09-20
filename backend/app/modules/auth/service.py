import re
from datetime import datetime, timedelta, timezone
from uuid import UUID
import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.users.model import User
from app.modules.auth.model import PasswordCredential, AuthSession, RefreshToken
from app.modules.auth import repository
from app.modules.auth import security
from app.modules.auth.schema import RegisterRequest, LoginRequest
from app.modules.auth.exceptions import (
    AuthenticationError, 
    InvalidSessionError, 
    DuplicateEmailError, 
    PasswordPolicyError
)
import structlog
logger = structlog.get_logger()

def _normalize_email(email: str) -> str:
    return email.strip().lower()

def _validate_password_policy(password: str) -> None:
    if len(password) < 15 or len(password) > 128:
        raise PasswordPolicyError("Password must be between 15 and 128 characters long.")

async def register_user(db: AsyncSession, data: RegisterRequest) -> tuple[User, str, str]:
    email = _normalize_email(data.email)
    _validate_password_policy(data.password)

    existing_user = await repository.get_user_by_email(db, email)
    if existing_user:
        raise DuplicateEmailError("Email already registered.")

    user = User(email=email)
    db.add(user)
    await db.flush()
    
    pwd_cred = PasswordCredential(
        user_id=user.id, 
        password_hash=security.hash_password(data.password)
    )
    db.add(pwd_cred)
    await db.flush()
    
    # Create session immediately
    return await _create_session_tokens(db, user.id)

async def login_user(db: AsyncSession, data: LoginRequest) -> tuple[User, str, str]:
    email = _normalize_email(data.email)
    user, cred = await repository.get_user_with_password_by_email(db, email)
    
    if not user or not cred:
        # Dummy verification to prevent timing attacks
        security.verify_dummy_password(data.password)
        raise AuthenticationError()
        
    if not security.verify_password(cred.password_hash, data.password):
        raise AuthenticationError()

    return await _create_session_tokens(db, user.id)

async def _create_session_tokens(db: AsyncSession, user_id: UUID) -> tuple[User, str, str]:
    now = datetime.now(timezone.utc)
    session_expires = now + timedelta(days=settings.session_max_age_days)
    refresh_expires = now + timedelta(days=settings.refresh_token_expire_days)
    # Clamp refresh expiry to session expiry
    if refresh_expires > session_expires:
        refresh_expires = session_expires

    auth_session = AuthSession(
        user_id=user_id,
        expires_at=session_expires
    )
    db.add(auth_session)
    await db.flush()
    
    raw_refresh = security.generate_refresh_token()
    refresh_record = RefreshToken(
        session_id=auth_session.id,
        token_hash=security.hash_refresh_token(raw_refresh),
        expires_at=refresh_expires
    )
    db.add(refresh_record)
    await db.commit()
    
    access_token = security.create_access_token(str(user_id), str(auth_session.id))
    user = await repository.get_user_by_id(db, user_id)
    return user, access_token, raw_refresh

async def refresh_session(db: AsyncSession, raw_refresh_token: str) -> tuple[str, str]:
    token_hash = security.hash_refresh_token(raw_refresh_token)
    
    token_record = await repository.get_refresh_token_for_update(db, token_hash)
    if not token_record:
        raise InvalidSessionError()
        
    now = datetime.now(timezone.utc)
    
    # Check expiry
    if token_record.expires_at < now:
        raise InvalidSessionError()
        
    # Reuse detection
    if token_record.replaced_at is not None:
        # REUSE DETECTED: Token was already used! Revoke session.
        await repository.revoke_auth_session(db, token_record.session_id, now)
        await db.commit() # MUST commit the revocation before raising!
        
        logger.warning("refresh_token_reuse_detected", session_id=str(token_record.session_id))
        raise InvalidSessionError()
        
    # Check if parent session is revoked or expired
    auth_session = await repository.get_auth_session(db, token_record.session_id)
    if not auth_session or auth_session.revoked_at or auth_session.expires_at < now:
        raise InvalidSessionError()
        
    # Rotate token
    token_record.replaced_at = now
    
    new_raw_refresh = security.generate_refresh_token()
    refresh_expires = now + timedelta(days=settings.refresh_token_expire_days)
    if refresh_expires > auth_session.expires_at:
        refresh_expires = auth_session.expires_at
        
    new_refresh_record = RefreshToken(
        session_id=auth_session.id,
        token_hash=security.hash_refresh_token(new_raw_refresh),
        expires_at=refresh_expires
    )
    db.add(new_refresh_record)
    await db.commit()
    
    access_token = security.create_access_token(str(auth_session.user_id), str(auth_session.id))
    
    return access_token, new_raw_refresh

async def logout_session(db: AsyncSession, raw_refresh_token: str) -> None:
    token_hash = security.hash_refresh_token(raw_refresh_token)
    token_record = await repository.get_refresh_token_for_update(db, token_hash)
    if token_record:
        now = datetime.now(timezone.utc)
        await repository.revoke_auth_session(db, token_record.session_id, now)
        await db.commit()
        # We don't raise if token is invalid during logout, just silently succeed.
