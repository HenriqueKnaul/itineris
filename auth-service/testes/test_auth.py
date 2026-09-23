"""Testes do auth-service.

Cobertura deliberadamente parcial: por enquanto so o health check tem
teste. O fluxo de login (app/api/auth.py) e o hashing/JWT
(app/core/security.py) ainda nao tem testes automatizados.
"""

def test_status_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "auth-service"}

def test_login_sucesso():
    response = client.post("/auth/login", json={"id": "admin", "password": "admin"})
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_alha():
    response = client.post("/auth/login", json={"id": "admin1", "password": "admin1"})
    assert response.status_code == 401 #verifica se deu erro 
    assert "access_token" in response.json()
