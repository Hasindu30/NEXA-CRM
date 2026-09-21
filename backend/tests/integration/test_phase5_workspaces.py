import asyncio
from uuid import uuid7
import pytest
from httpx import AsyncClient, ASGITransport
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch

from app.main import app
from app.modules.users.model import User
from app.modules.workspaces.model import Workspace, WorkspaceMembership

pytestmark = pytest.mark.asyncio(loop_scope="session")

@pytest.fixture
async def async_client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), 
        base_url="http://test",
        headers={"Origin": "http://localhost:3000"} 
    ) as client:
        yield client

async def get_auth_token(client: AsyncClient, email: str) -> str:
    res = await client.post("/api/v1/auth/register", json={"email": email, "password": "SuperStrongPassword123"})
    if res.status_code == 409:
        res = await client.post("/api/v1/auth/login", json={"email": email, "password": "SuperStrongPassword123"})
    return res.json()["access_token"]

async def test_unauthenticated_cannot_create_workspace(async_client: AsyncClient):
    # 4. Unauthenticated user cannot create workspace
    res = await async_client.post("/api/v1/workspaces", json={"name": "My Workspace"})
    assert res.status_code == 401

async def test_create_workspace_and_membership(async_client: AsyncClient, db_session: AsyncSession):
    # 1. Authenticated user creates workspace
    token = await get_auth_token(async_client, "creator@test.com")
    res = await async_client.post("/api/v1/workspaces", json={"name": "Creator Workspace"}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Creator Workspace"
    assert data["slug"] == "creator-workspace"
    workspace_id = data["id"]
    
    # 2. Creator automatically becomes member
    # Direct DB check to ensure membership exists
    member = await db_session.execute(sa.select(WorkspaceMembership).where(WorkspaceMembership.workspace_id == workspace_id))
    member = member.scalar_one()
    
    user = await db_session.execute(sa.select(User).where(User.email == "creator@test.com"))
    user = user.scalar_one()
    
    assert member.user_id == user.id

async def test_workspace_creation_atomicity(async_client: AsyncClient, db_session: AsyncSession):
    # 3. Workspace + membership creation is atomic
    token = await get_auth_token(async_client, "atomic@test.com")
    
    from sqlalchemy.ext.asyncio import AsyncSession
    original_add = AsyncSession.add
    
    def mock_add(self, obj, *args, **kwargs):
        if isinstance(obj, WorkspaceMembership):
            raise RuntimeError("Simulated failure during membership insertion")
        return original_add(self, obj, *args, **kwargs)
        
    with patch("sqlalchemy.ext.asyncio.AsyncSession.add", new=mock_add):
        try:
            res = await async_client.post("/api/v1/workspaces", json={"name": "Atomic Rollback"}, headers={"Authorization": f"Bearer {token}"})
            assert res.status_code == 500
        except RuntimeError as e:
            assert "Simulated failure" in str(e)
            
    # Verify no orphan workspace row remains
    orphans = await db_session.execute(sa.select(Workspace).where(Workspace.name == "Atomic Rollback"))
    assert orphans.first() is None
    
    # Verify no membership remains
    user = await db_session.execute(sa.select(User).where(User.email == "atomic@test.com"))
    user = user.scalar_one()
    member = await db_session.execute(sa.select(WorkspaceMembership).where(WorkspaceMembership.user_id == user.id))
    assert member.first() is None

async def test_workspace_name_length_validation(async_client: AsyncClient):
    token = await get_auth_token(async_client, "length@test.com")
    
    # Exactly 100 characters should pass
    name_100 = "A" * 100
    res_100 = await async_client.post("/api/v1/workspaces", json={"name": name_100}, headers={"Authorization": f"Bearer {token}"})
    assert res_100.status_code == 201
    
    # 100 characters + trailing spaces should pass because they are stripped first
    name_100_spaces = "B" * 100 + "   "
    res_100_s = await async_client.post("/api/v1/workspaces", json={"name": name_100_spaces}, headers={"Authorization": f"Bearer {token}"})
    assert res_100_s.status_code == 201
    
    # 101 characters should fail with 422
    name_101 = "C" * 101
    res_101 = await async_client.post("/api/v1/workspaces", json={"name": name_101}, headers={"Authorization": f"Bearer {token}"})
    assert res_101.status_code == 422
    
    # All whitespace should fail with 422
    res_empty = await async_client.post("/api/v1/workspaces", json={"name": "    "}, headers={"Authorization": f"Bearer {token}"})
    assert res_empty.status_code == 422

async def test_list_workspaces_isolation(async_client: AsyncClient):
    # 5. Authenticated user lists only workspaces they belong to
    # 6. User cannot see unrelated workspace
    # 15. Queries do not accidentally expose workspaces across tenants
    token_a = await get_auth_token(async_client, "user_a@test.com")
    token_b = await get_auth_token(async_client, "user_b@test.com")
    
    res_a = await async_client.post("/api/v1/workspaces", json={"name": "Workspace A"}, headers={"Authorization": f"Bearer {token_a}"})
    ws_a = res_a.json()["id"]
    
    res_b = await async_client.post("/api/v1/workspaces", json={"name": "Workspace B"}, headers={"Authorization": f"Bearer {token_b}"})
    
    list_a = await async_client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token_a}"})
    assert len(list_a.json()["data"]) == 1
    assert list_a.json()["data"][0]["name"] == "Workspace A"
    
    # 8. Non-member cannot resolve workspace context
    get_b_with_a = await async_client.get(f"/api/v1/workspaces/{ws_a}", headers={"Authorization": f"Bearer {token_b}"})
    assert get_b_with_a.status_code == 404 # same safe 404
    
    # 7. Valid member can resolve workspace context
    get_a_with_a = await async_client.get(f"/api/v1/workspaces/{ws_a}", headers={"Authorization": f"Bearer {token_a}"})
    assert get_a_with_a.status_code == 200
    assert get_a_with_a.json()["name"] == "Workspace A"

async def test_invalid_workspace_id(async_client: AsyncClient):
    # 9. Invalid workspace ID safely rejected
    token = await get_auth_token(async_client, "invalid@test.com")
    res = await async_client.get("/api/v1/workspaces/not-a-uuid", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 422 # FastAPI standard for invalid UUID path parameter
    
    res2 = await async_client.get(f"/api/v1/workspaces/{uuid7()}", headers={"Authorization": f"Bearer {token}"})
    assert res2.status_code == 404 # Non-existent UUID gives safe 404

async def test_slug_normalization_and_collision(async_client: AsyncClient):
    # 10. Workspace slug normalization succeeds
    # 11. Workspace slug collision handling correctly applies suffix
    token = await get_auth_token(async_client, "slug@test.com")
    
    res1 = await async_client.post("/api/v1/workspaces", json={"name": "   My % Crazy @ Workspace!!  "}, headers={"Authorization": f"Bearer {token}"})
    assert res1.status_code == 201
    assert res1.json()["slug"] == "my-crazy-workspace"
    
    # Collision!
    res2 = await async_client.post("/api/v1/workspaces", json={"name": "My % Crazy @ Workspace!!"}, headers={"Authorization": f"Bearer {token}"})
    assert res2.status_code == 201
    
    slug2 = res2.json()["slug"]
    assert slug2.startswith("my-crazy-workspace-")
    assert len(slug2) > len("my-crazy-workspace-") # Suffix applied

async def test_empty_normalized_slug_fallback(async_client: AsyncClient):
    token = await get_auth_token(async_client, "empty_slug@test.com")
    # All non-alphanumeric
    res = await async_client.post("/api/v1/workspaces", json={"name": "@@@@"}, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 201
    assert res.json()["slug"].startswith("workspace-") or res.json()["slug"] == "workspace"

async def test_multi_membership(async_client: AsyncClient, db_session: AsyncSession):
    # 13. One user can belong to multiple workspaces
    # 14. Two different users can belong to same workspace
    token_u1 = await get_auth_token(async_client, "u1@test.com")
    token_u2 = await get_auth_token(async_client, "u2@test.com")
    
    res1 = await async_client.post("/api/v1/workspaces", json={"name": "U1 W1"}, headers={"Authorization": f"Bearer {token_u1}"})
    ws1_id = res1.json()["id"]
    
    res2 = await async_client.post("/api/v1/workspaces", json={"name": "U1 W2"}, headers={"Authorization": f"Bearer {token_u1}"})
    ws2_id = res2.json()["id"]
    
    # Check U1 has 2 workspaces
    list_u1 = await async_client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token_u1}"})
    assert len(list_u1.json()["data"]) == 2
    
    # Manually add U2 to W1 in DB
    u2 = await db_session.execute(sa.select(User).where(User.email == "u2@test.com"))
    u2 = u2.scalar_one()
    
    # 12. Duplicate membership prevented by DB
    from app.db.session import engine as app_engine
    async with AsyncSession(app_engine) as app_db:
        # Add U2 to W1
        app_db.add(WorkspaceMembership(user_id=u2.id, workspace_id=ws1_id))
        await app_db.commit()
        
        # Test 14: Two different users in same workspace
        list_u2 = await async_client.get("/api/v1/workspaces", headers={"Authorization": f"Bearer {token_u2}"})
        assert len(list_u2.json()["data"]) == 1
        assert list_u2.json()["data"][0]["id"] == ws1_id
        
        # Test 12: Try to insert duplicate membership
        try:
            app_db.add(WorkspaceMembership(user_id=u2.id, workspace_id=ws1_id))
            await app_db.commit()
            assert False, "Should have failed unique constraint"
        except Exception as e:
            await app_db.rollback()
            assert "uq_workspace_memberships" in str(e) or "UniqueViolationError" in str(e) or "duplicate key" in str(e)
