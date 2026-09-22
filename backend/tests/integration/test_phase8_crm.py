import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from app.modules.companies.model import Company
from app.modules.people.model import Person

pytestmark = pytest.mark.asyncio(loop_scope="session")

from app.main import app
from httpx import ASGITransport

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

@pytest.fixture
async def owner_token(async_client: AsyncClient) -> str:
    return await get_auth_token(async_client, "owner@test.com")

@pytest.fixture
async def admin_token(async_client: AsyncClient, owner_token: str, workspace: dict) -> str:
    token = await get_auth_token(async_client, "admin@test.com")
    await async_client.post(f"/api/v1/workspaces/{workspace['id']}/members", json={"email": "admin@test.com"}, headers={"Authorization": f"Bearer {owner_token}"})
    # Find user_id and promote to admin
    res = await async_client.get(f"/api/v1/workspaces/{workspace['id']}/members", headers={"Authorization": f"Bearer {owner_token}"})
    user_id = next(m["user_id"] for m in res.json()["data"] if m["email"] == "admin@test.com")
    await async_client.patch(f"/api/v1/workspaces/{workspace['id']}/members/{user_id}/role", json={"role": "admin"}, headers={"Authorization": f"Bearer {owner_token}"})
    return token

@pytest.fixture
async def member_token(async_client: AsyncClient, owner_token: str, workspace: dict) -> str:
    token = await get_auth_token(async_client, "member@test.com")
    await async_client.post(f"/api/v1/workspaces/{workspace['id']}/members", json={"email": "member@test.com"}, headers={"Authorization": f"Bearer {owner_token}"})
    return token

@pytest.fixture
async def user_token(async_client: AsyncClient) -> str:
    return await get_auth_token(async_client, "stranger@test.com")

@pytest.fixture
async def workspace(async_client: AsyncClient, owner_token: str) -> dict:
    import uuid
    res = await async_client.post("/api/v1/workspaces", json={"name": f"Test WS {uuid.uuid4()}"}, headers={"Authorization": f"Bearer {owner_token}"})
    return res.json()

async def test_crm_permissions(
    async_client: AsyncClient,
    owner_token: str,
    admin_token: str,
    member_token: str,
    user_token: str, # Not in workspace
    workspace: dict
):
    ws_id = workspace["id"]
    
    # 1. Non-member -> 404
    resp = await async_client.get(f"/api/v1/workspaces/{ws_id}/companies", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 404
    
    # 2. Member can create company
    resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/companies", 
        json={"name": "Member Company"},
        headers={"Authorization": f"Bearer {member_token}"}
    )
    assert resp.status_code == 201
    comp_id = resp.json()["id"]
    
    # 3. Admin can read and update
    resp = await async_client.patch(
        f"/api/v1/workspaces/{ws_id}/companies/{comp_id}",
        json={"domain": "admin.com"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["domain"] == "admin.com"
    
    # 4. Owner can delete
    resp = await async_client.delete(
        f"/api/v1/workspaces/{ws_id}/companies/{comp_id}",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert resp.status_code == 204

async def test_cross_workspace_isolation(
    async_client: AsyncClient,
    owner_token: str,
    workspace: dict,
    db_session: AsyncSession
):
    # Setup second workspace via API
    u2_token = await get_auth_token(async_client, "u2@test.com")
    resp = await async_client.post("/api/v1/workspaces", json={"name": "WS2"}, headers={"Authorization": f"Bearer {u2_token}"})
    ws2_id = resp.json()["id"]
    
    # Create company in ws1
    resp = await async_client.post(
        f"/api/v1/workspaces/{workspace['id']}/companies", 
        json={"name": "WS1 Company"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    ws1_comp_id = resp.json()["id"]
    
    # Create person in ws1
    resp = await async_client.post(
        f"/api/v1/workspaces/{workspace['id']}/people", 
        json={"first_name": "WS1 Person"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    ws1_person_id = resp.json()["id"]
    
    # We shouldn't be able to read/update/delete these using ws2's ID, even as an owner of ws1, 
    # but wait, the API endpoint is /workspaces/{ws_id}/....
    # If we pass ws2's ID, but owner_token is used... owner is NOT a member of ws2, so they get 404 on the workspace itself.
    # What if we use u2's token (owner of ws2) to access ws1's company?
    # Let's mock a token for u2 or just test API validation:
    
    # If we are in WS1, can we assign a company from WS2 to a person in WS1?
    # Create company in WS2 directly in DB
    c2 = Company(workspace_id=ws2_id, name="WS2 Company")
    db_session.add(c2)
    await db_session.commit()
    
    # Try to assign WS2 company to WS1 person using WS1 owner token
    resp = await async_client.patch(
        f"/api/v1/workspaces/{workspace['id']}/people/{ws1_person_id}",
        json={"company_id": str(c2.id)},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert resp.status_code == 404 # "Company not found in this workspace"
    
    # Try to read WS1 company using WS2 ID
    resp = await async_client.get(
        f"/api/v1/workspaces/{ws2_id}/companies/{ws1_comp_id}",
        headers={"Authorization": f"Bearer {owner_token}"} # Although owner is not in ws2, this hits the 404 from WorkspaceNotFoundError first!
    )
    assert resp.status_code == 404
    
    # We already generated u2_token for the owner of WS2
    resp = await async_client.get(
        f"/api/v1/workspaces/{ws2_id}/companies/{ws1_comp_id}",
        headers={"Authorization": f"Bearer {u2_token}"}
    )
    assert resp.status_code == 404
    
    resp = await async_client.delete(
        f"/api/v1/workspaces/{ws2_id}/people/{ws1_person_id}",
        headers={"Authorization": f"Bearer {u2_token}"}
    )
    assert resp.status_code == 404

    # Test DB level composite FK violation
    p = Person(workspace_id=ws2_id, first_name="Hacker", company_id=ws1_comp_id)
    db_session.add(p)
    with pytest.raises(IntegrityError) as exc:
        await db_session.commit()
    assert "fk_people_workspace_id_company_id_companies" in str(exc.value)
    await db_session.rollback()

async def test_person_identity_validation(
    async_client: AsyncClient,
    owner_token: str,
    workspace: dict
):
    ws_id = workspace["id"]
    
    # 1. Missing all identity
    resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/people", 
        json={"job_title": "Ghost"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert resp.status_code == 422
    
    # 2. Whitespace only identity
    resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/people", 
        json={"first_name": "   ", "last_name": "", "email": None},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert resp.status_code == 422
    
    # 3. Valid identity
    resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/people", 
        json={"first_name": "Valid"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert resp.status_code == 201
    person_id = resp.json()["id"]
    
    # 4. PATCH removing identity fails
    resp = await async_client.patch(
        f"/api/v1/workspaces/{ws_id}/people/{person_id}", 
        json={"first_name": "  "},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert resp.status_code == 422

async def test_company_delete_transaction(
    async_client: AsyncClient,
    owner_token: str,
    workspace: dict
):
    ws_id = workspace["id"]
    
    # Create company
    resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/companies", 
        json={"name": "To Be Deleted"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    comp_id = resp.json()["id"]
    
    # Create person linked
    resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/people", 
        json={"first_name": "Survivor", "company_id": comp_id},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    person_id = resp.json()["id"]
    assert resp.json()["company_id"] == comp_id
    
    # Delete company
    resp = await async_client.delete(
        f"/api/v1/workspaces/{ws_id}/companies/{comp_id}",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert resp.status_code == 204
    
    # Person survives with null company
    resp = await async_client.get(
        f"/api/v1/workspaces/{ws_id}/people/{person_id}",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["company_id"] is None
    assert resp.json()["company"] is None

async def test_patch_omitted_vs_explicit_null(
    async_client: AsyncClient,
    owner_token: str,
    workspace: dict
):
    ws_id = workspace["id"]
    
    # Setup company and person
    resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/companies", 
        json={"name": "My Co"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    comp_id = resp.json()["id"]
    
    resp = await async_client.post(
        f"/api/v1/workspaces/{ws_id}/people", 
        json={"first_name": "Link", "company_id": comp_id, "job_title": "Dev"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    person_id = resp.json()["id"]
    
    # Omitted fields do not change
    resp = await async_client.patch(
        f"/api/v1/workspaces/{ws_id}/people/{person_id}", 
        json={"first_name": "Linked"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["company_id"] == comp_id
    assert resp.json()["job_title"] == "Dev"
    
    # Explicit null unlinks
    resp = await async_client.patch(
        f"/api/v1/workspaces/{ws_id}/people/{person_id}", 
        json={"company_id": None},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["company_id"] is None
    
async def test_pagination_and_search(
    async_client: AsyncClient,
    owner_token: str,
    workspace: dict
):
    ws_id = workspace["id"]
    
    # Create 3 companies
    for i in range(3):
        await async_client.post(f"/api/v1/workspaces/{ws_id}/companies", json={"name": f"Comp {i}"}, headers={"Authorization": f"Bearer {owner_token}"})
        
    # Search
    resp = await async_client.get(f"/api/v1/workspaces/{ws_id}/companies?q=Comp 1", headers={"Authorization": f"Bearer {owner_token}"})
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1
    assert resp.json()["data"][0]["name"] == "Comp 1"
    
    # Pagination limit
    resp = await async_client.get(f"/api/v1/workspaces/{ws_id}/companies?limit=2", headers={"Authorization": f"Bearer {owner_token}"})
    data = resp.json()
    assert len(data["data"]) == 2
    assert data["meta"]["total"] == 3
    assert data["meta"]["page"] == 1
    assert data["meta"]["total_pages"] == 2

async def test_person_crud(
    async_client: AsyncClient,
    owner_token: str,
    workspace: dict
):
    ws_id = workspace["id"]
    
    # Create
    resp = await async_client.post(f"/api/v1/workspaces/{ws_id}/people", json={"first_name": "Test Person"}, headers={"Authorization": f"Bearer {owner_token}"})
    assert resp.status_code == 201
    person_id = resp.json()["id"]
    
    # Get
    resp = await async_client.get(f"/api/v1/workspaces/{ws_id}/people/{person_id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert resp.status_code == 200
    assert resp.json()["first_name"] == "Test Person"
    
    # List
    resp = await async_client.get(f"/api/v1/workspaces/{ws_id}/people", headers={"Authorization": f"Bearer {owner_token}"})
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1
    
    # Update
    resp = await async_client.patch(f"/api/v1/workspaces/{ws_id}/people/{person_id}", json={"last_name": "Updated"}, headers={"Authorization": f"Bearer {owner_token}"})
    assert resp.status_code == 200
    assert resp.json()["last_name"] == "Updated"
    
    # Delete
    resp = await async_client.delete(f"/api/v1/workspaces/{ws_id}/people/{person_id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert resp.status_code == 204
    
    # Get again -> 404
    resp = await async_client.get(f"/api/v1/workspaces/{ws_id}/people/{person_id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert resp.status_code == 404
