from fastapi.testclient import TestClient
import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.main import app
from app.models import Voo


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as sessao:
        yield sessao
    engine.dispose()


@pytest.fixture
def catalogo(session):
    dados = [
        ("Brasil", "Lisboa", 1000.0, 100, 100),
        ("Lisboa", "Paris", 500.0, 100, 100),
        ("Paris", "Brasil", 1000.0, 100, 100),
    ]
    for origem, destino, preco, capacidade, vagas in dados:
        session.add(Voo(origem=origem, destino=destino, preco_base=preco, capacidade=capacidade, vagas=vagas))
    session.commit()


@pytest.fixture
def client(session, catalogo):
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()