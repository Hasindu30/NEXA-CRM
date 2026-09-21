import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

pytestmark = pytest.mark.asyncio(loop_scope="session")

async def test_readiness_check():
    """
    Test the readiness endpoint.
    This requires a real PostgreSQL connection to succeed (HTTP 200).
    If the database is down, this will return HTTP 503.
    Uses AsyncClient/ASGITransport so the request runs inside the shared
    pytest-asyncio session event loop and never creates a competing
    asyncio.run() that would strand asyncpg connections on a closed loop.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}
