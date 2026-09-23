from fastapi.testclient import TestClient
from jose import jwt

from app.main import ALGORITHM, SECRET_KEY, app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy", "service": "auth-service"}


def test_login_sucesso():
    r = client.post("/auth/login", json={"id": "admin", "password": "admin"})
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["token_type"] == "bearer"
    # o gateway valida com a mesma chave, então o token tem que abrir com ela
    claims = jwt.decode(corpo["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert claims["sub"] == "admin"


def test_login_senha_errada():
    r = client.post("/auth/login", json={"id": "admin", "password": "errada"})
    assert r.status_code == 401
    assert "access_token" not in r.json()


def test_login_usuario_inexistente():
    r = client.post("/auth/login", json={"id": "fulano", "password": "admin"})
    assert r.status_code == 401
