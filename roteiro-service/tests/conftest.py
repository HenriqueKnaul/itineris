from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.main import app


@pytest.fixture
def session():
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
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def payload_roteiro():
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
