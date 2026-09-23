"""Fixtures compartilhadas: banco SQLite em memória (não usa o auth_database.db real)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.security import gerar_hash_senha
from app.domain.models import Usuario
from app.infrastructure.database import get_session
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
        sessao.add(Usuario(id="admin", nome="Administrador", hashed_password=gerar_hash_senha("admin")))
        sessao.commit()
        yield sessao
    engine.dispose()


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def client_sem_bd():
    """Cliente simples para rotas que não tocam o banco (ex.: /health)."""
    return TestClient(app)
