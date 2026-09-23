"""Fixtures compartilhadas: banco SQLite em memória e cliente HTTP de teste."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.infrastructure.database import get_session
from app.main import app


@pytest.fixture
def session():
    """Banco novo (em memória) para cada teste: nada vaza entre testes."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as sessao:
        yield sessao
    engine.dispose()


@pytest.fixture
def client(session):
    """Cliente HTTP usando o mesmo banco em memória do teste (mesma sessão em
    todas as chamadas, o que permite o teste monkeypatchar session.commit
    quando precisa simular uma falha no meio da Saga)."""
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def payload_roteiro():
    """Corpo de exemplo para criar um roteiro com um destino."""
    inicio = date.today() + timedelta(days=30)
    return {
        "titulo": "Férias na Europa",
        "data_inicio": inicio.isoformat(),
        "data_fim": (inicio + timedelta(days=10)).isoformat(),
        "orcamento_teto": 5000.0,
        "usuario_id": 1,
        "destinos": [
            {
                "cidade": "Lisboa",
                "pais": "Portugal",
                "data_chegada": inicio.isoformat(),
                "data_partida": (inicio + timedelta(days=10)).isoformat(),
                "ordem": 1,
            }
        ],
    }
