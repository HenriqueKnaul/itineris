from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "auth-service"}

def test_login_sucesso():
    response = client.post("/auth/login", json={"id": "admin", "password": "admin"})
    assert response.status_code == 200
    assert "access_token" in response.json()