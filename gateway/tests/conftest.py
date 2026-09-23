"""Fixtures compartilhadas dos testes do gateway."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.seguranca import ALGORITHM, SECRET_KEY
from app.main import app


@pytest.fixture
def client():
    """TestClient com o lifespan real (cria/fecha o httpx.AsyncClient do gateway)."""
    with TestClient(app) as cliente:
        yield cliente


@pytest.fixture
def token_valido():
    """Token assinado com a mesma chave que o gateway usa para validar."""
    dados = {"sub": "admin", "exp": datetime.now(timezone.utc) + timedelta(minutes=30)}
    return jwt.encode(dados, SECRET_KEY, algorithm=ALGORITHM)


@pytest.fixture
def token_expirado():
    dados = {"sub": "admin", "exp": datetime.now(timezone.utc) - timedelta(minutes=5)}
    return jwt.encode(dados, SECRET_KEY, algorithm=ALGORITHM)
