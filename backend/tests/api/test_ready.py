from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_readiness_check():
    """
    Test the readiness endpoint.
    This requires a real PostgreSQL connection to succeed (HTTP 200).
    If the database is down, this will return HTTP 503.
    """
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}
