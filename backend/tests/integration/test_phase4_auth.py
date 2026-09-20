import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid7
import pytest
from httpx import AsyncClient, ASGITransport
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
import jwt

from app.main import app
from app.core.config import settings
from app.modules.users.model import User
from app.modules.workspaces.model import WorkspaceMembership, Workspace
from app.modules.auth.model import PasswordCredential, AuthSession, RefreshToken
from app.modules.auth import security

pytestmark = pytest.mark.asyncio(loop_scope="session")

@pytest.fixture
async def async_client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), 
        base_url="http://test",
        headers={"Origin": "http://localhost:3000"} 
    ) as client:
        yield client

async def test_successful_registration_and_jwt_claims(async_client: AsyncClient, db_session: AsyncSession):
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "NEW@Example.COM", "password": "SuperStrongPassword123"}
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "new@example.com"
    
    assert "refresh_token" in response.cookies
    cookie = response.cookies["refresh_token"]
    assert cookie is not None
    set_cookie_header = response.headers.get("set-cookie")
    assert "Path=/api/v1/auth" in set_cookie_header
    assert "HttpOnly" in set_cookie_header
    assert "samesite=strict" in set_cookie_header.lower()
    
    access_token = data["access_token"]
    payload = security.decode_access_token(access_token)
    assert payload["typ"] == "access"
    assert "sub" in payload
    assert "sid" in payload
    assert "exp" in payload

    user = await db_session.execute(sa.select(User).where(User.email == "new@example.com"))
    user = user.scalar_one()
    cred = await db_session.execute(sa.select(PasswordCredential).where(PasswordCredential.user_id == user.id))
    cred = cred.scalar_one()
    
    assert cred.password_hash.startswith("$argon2id$")
    assert "SuperStrongPassword123" not in cred.password_hash

async def test_duplicate_registration_fails(async_client: AsyncClient):
    await async_client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "SuperStrongPassword123"}
    )
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "SuperStrongPassword123"}
    )
    assert response.status_code == 409

async def test_invalid_origin_fails(db_session: AsyncSession):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers={"Origin": "http://evil.com"}) as evil_client:
        response = await evil_client.post(
            "/api/v1/auth/register",
            json={"email": "evil@example.com", "password": "SuperStrongPassword123"}
        )
        assert response.status_code == 403

async def test_login_success(async_client: AsyncClient):
    await async_client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": "SuperStrongPassword123"}
    )
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "SuperStrongPassword123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.cookies

async def test_login_failures(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "SuperStrongPassword123"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."
    
    await async_client.post(
        "/api/v1/auth/register",
        json={"email": "wrongpass@example.com", "password": "SuperStrongPassword123"}
    )
    response2 = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpass@example.com", "password": "WrongPassword456"}
    )
    assert response2.status_code == 401
    assert response2.json()["detail"] == "Invalid email or password."

async def test_refresh_and_reuse_flow(async_client: AsyncClient, db_session: AsyncSession):
    reg_res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "refresh@example.com", "password": "SuperStrongPassword123"}
    )
    original_refresh = reg_res.cookies["refresh_token"]
    original_access = reg_res.json()["access_token"]
    
    me_res = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {original_access}"})
    assert me_res.status_code == 200
    
    refresh_res = await async_client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": original_refresh}
    )
    assert refresh_res.status_code == 200
    new_access = refresh_res.json()["access_token"]
    new_refresh = refresh_res.cookies["refresh_token"]
    
    me_res2 = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me_res2.status_code == 200
    
    reuse_res = await async_client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": original_refresh}
    )
    assert reuse_res.status_code == 401 
    
    me_res3 = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me_res3.status_code == 401
    
    payload = security.decode_access_token(new_access)
    session_id = payload["sid"]
    session_row = await db_session.execute(sa.select(AuthSession).where(AuthSession.id == session_id))
    session = session_row.scalar_one()
    assert session.revoked_at is not None

async def test_logout(async_client: AsyncClient):
    reg_res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "logout@example.com", "password": "SuperStrongPassword123"}
    )
    refresh_token = reg_res.cookies["refresh_token"]
    access_token = reg_res.json()["access_token"]
    
    logout_res = await async_client.post(
        "/api/v1/auth/logout",
        cookies={"refresh_token": refresh_token}
    )
    assert logout_res.status_code == 200
    
    set_cookie = logout_res.headers.get("set-cookie", "")
    assert "refresh_token=;" in set_cookie or "Max-Age=0" in set_cookie
    
    me_res = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_res.status_code == 401

async def test_raw_refresh_token_never_stored(async_client: AsyncClient, db_session: AsyncSession):
    reg_res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "raw@example.com", "password": "SuperStrongPassword123"}
    )
    raw_token = reg_res.cookies["refresh_token"]
    
    tokens = await db_session.execute(sa.select(RefreshToken.token_hash))
    hashes = tokens.scalars().all()
    for th in hashes:
        assert th != raw_token 
        
async def test_refresh_token_concurrent_execution(async_client: AsyncClient):
    reg_res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "concurrent@example.com", "password": "SuperStrongPassword123"}
    )
    raw_token = reg_res.cookies["refresh_token"]
    
    res1, res2 = await asyncio.gather(
        async_client.post("/api/v1/auth/refresh", cookies={"refresh_token": raw_token}),
        async_client.post("/api/v1/auth/refresh", cookies={"refresh_token": raw_token})
    )
    statuses = [res1.status_code, res2.status_code]
    assert 200 in statuses
    assert 401 in statuses

async def test_invalid_and_expired_access_jwt(async_client: AsyncClient):
    res = await async_client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalidtoken"})
    assert res.status_code == 401
    
    expired_token = jwt.encode(
        {"sub": str(uuid7()), "sid": str(uuid7()), "typ": "access", "exp": datetime.now(timezone.utc) - timedelta(minutes=5)},
        settings.jwt_signing_key, algorithm=settings.jwt_algorithm
    )
    res2 = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res2.status_code == 401

async def test_expired_auth_session_rejects_jwt(async_client: AsyncClient, db_session: AsyncSession):
    reg_res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "exp_sess@example.com", "password": "SuperStrongPassword123"}
    )
    access_token = reg_res.json()["access_token"]
    
    payload = security.decode_access_token(access_token)
    session_id = payload["sid"]
    
    from app.db.session import engine as app_engine
    async with AsyncSession(app_engine) as app_db:
        await app_db.execute(
            sa.update(AuthSession)
            .where(AuthSession.id == session_id)
            .values(expires_at=sa.func.now() - timedelta(days=1))
        )
        await app_db.commit()
    
    res = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert res.status_code == 401

async def test_refresh_expiry_never_exceeds_auth_session(async_client: AsyncClient, db_session: AsyncSession):
    reg_res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "clamp@example.com", "password": "SuperStrongPassword123"}
    )
    
    payload = security.decode_access_token(reg_res.json()["access_token"])
    session_id = payload["sid"]
    
    # Fetch refresh token
    refresh_record = await db_session.execute(
        sa.select(RefreshToken).where(RefreshToken.session_id == session_id)
    )
    refresh_obj = refresh_record.scalar_one()
    
    auth_sess = await db_session.execute(
        sa.select(AuthSession).where(AuthSession.id == session_id)
    )
    session_obj = auth_sess.scalar_one()
    
    assert refresh_obj.expires_at <= session_obj.expires_at
