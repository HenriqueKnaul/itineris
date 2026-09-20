"""Fixtures compartilhadas: banco SQLite em memória, catálogo de teste e cliente HTTP."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.application.commands.reservar_roteiro import ReservarRoteiroCommand
from app.domain.models import Voo
from app.domain.regras import DestinoRoteiro
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
def hoje():
    """Data fixa para que a regra de antecedência seja determinística."""
    return date(2026, 1, 1)


@pytest.fixture
def catalogo(session):
    """Catálogo controlado (preços redondos, sem acréscimo por ocupação).

    Roteiro Lisboa -> Paris: Brasil->Lisboa (1000) + Lisboa->Paris (500)
    + Paris->Brasil (1000) = 2500.
    """
    dados = [
        ("Brasil", "Lisboa", 1000.0, 100, 100),
        ("Lisboa", "Paris", 500.0, 100, 100),
        ("Paris", "Brasil", 1000.0, 100, 100),
        ("Paris", "Lisboa", 500.0, 100, 100),
        ("Lisboa", "Brasil", 1000.0, 100, 100),
        ("Brasil", "Tóquio", 3000.0, 100, 0),  # esgotado
        ("Tóquio", "Brasil", 3000.0, 100, 50),
    ]
    voos = {}
    for origem, destino, preco, capacidade, vagas in dados:
        voo = Voo(origem=origem, destino=destino, preco_base=preco, capacidade=capacidade, vagas=vagas)
        session.add(voo)
        voos[(origem, destino)] = voo
    session.commit()
    return voos


@pytest.fixture
def novo_comando():
    """Fábrica de comandos de reserva com datas distantes (dez/2026)."""

    def _criar(roteiro_id=1, teto=3000.0, cidades=("Lisboa", "Paris")):
        destinos = []
        inicio = date(2026, 12, 10)
        for i, cidade in enumerate(cidades):
            chegada = inicio + timedelta(days=5 * i)
            destinos.append(DestinoRoteiro(cidade, chegada, chegada + timedelta(days=5)))
        return ReservarRoteiroCommand(roteiro_id=roteiro_id, teto_financeiro=teto, destinos=destinos)

    return _criar


@pytest.fixture
def client(session, catalogo):
    """Cliente HTTP usando o mesmo banco em memória dos testes."""
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()
