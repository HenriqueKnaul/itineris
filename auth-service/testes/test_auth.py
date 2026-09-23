"""Testes do auth-service.

Cobertura deliberadamente parcial: por enquanto so o health check tem
teste. O fluxo de login (app/api/auth.py) e o hashing/JWT
(app/core/security.py) ainda nao tem testes automatizados.
"""


def test_health_check(client_sem_bd):
    resposta = client_sem_bd.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "healthy", "service": "auth-service"}
