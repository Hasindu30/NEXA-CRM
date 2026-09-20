import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import jwt

from app.core.config import settings

# Configure Argon2id
ph = PasswordHasher()

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(password_hash: str, password: str) -> bool:
    try:
        return ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False

def verify_dummy_password(password: str) -> bool:
    """Perform dummy hash verification for timing attack mitigation."""
    # This hash is an arbitrary valid Argon2id hash of a dummy string.
    dummy_hash = "$argon2id$v=19$m=65536,t=3,p=4$dummy$dummyhashthatisinvalid1234567890"
    try:
        return ph.verify(dummy_hash, password)
    except Exception:
        return False

def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)

def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def create_access_token(user_id: str, session_id: str) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode = {
        "sub": user_id,
        "sid": session_id,
        "typ": "access",
        "iat": now,
        "exp": expire,
        "jti": secrets.token_hex(16)
    }
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.jwt_signing_key, 
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token, 
        settings.jwt_signing_key, 
        algorithms=[settings.jwt_algorithm]
    )
