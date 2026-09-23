"""Testes de integração das rotas de roteiro (FastAPI TestClient + banco em memória).

Cobertura deliberadamente parcial: o foco aqui é o fluxo principal (CRUD),
a validação de datas, o cascade delete e a Saga de reserva — incluindo o
caso de compensação quando o commit local falha depois da aprovação remota.
"""
from unittest.mock import AsyncMock

import app.api.roteiro as roteiro_api
from app.infrastructure.cotacao_client import ReservaAprovada


def test_criar_roteiro_com_destinos(client, payload_roteiro, session):
    from sqlmodel import select

    from app.domain.models import Destino

    resposta = client.post("/roteiros/", json=payload_roteiro)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["titulo"] == "Férias na Europa"
    assert corpo["status"] == "RASCUNHO"
    destinos_gravados = session.exec(
        select(Destino).where(Destino.roteiro_id == corpo["id"])
    ).all()
    assert len(destinos_gravados) == 1
    assert destinos_gravados[0].cidade == "Lisboa"


def test_deletar_roteiro_remove_os_destinos_em_cascata(client, payload_roteiro, session):
    from app.domain.models import Destino

    roteiro_id = client.post("/roteiros/", json=payload_roteiro).json()["id"]

    resposta = client.delete(f"/roteiros/{roteiro_id}")

    assert resposta.status_code == 204
    assert client.get(f"/roteiros/{roteiro_id}").status_code == 404
    # Sem o cascade, o destino ficaria órfão no banco (FK "pendurada").
    assert session.get(Destino, 1) is None


def test_reservar_roteiro_compensa_quando_commit_local_falha(
    client, payload_roteiro, session, monkeypatch
):
    """Aprova a reserva no cotacao-service, mas força o commit local a
    explodir: a rota precisa acionar a compensação (cancelar_passagens) em
    vez de deixar o roteiro "preso" entre os dois bancos."""
    roteiro_id = client.post("/roteiros/", json=payload_roteiro).json()["id"]

    aprovado = ReservaAprovada(
        status="aprovado",
        valor_total=1000.0,
        saldo_restante=4000.0,
        reservas=[{"reserva_id": 1, "origem": "Brasil", "destino": "Lisboa"}],
    )
    monkeypatch.setattr(roteiro_api, "reservar_passagens", AsyncMock(return_value=aprovado))
    cancelar_mock = AsyncMock(return_value=1)
    monkeypatch.setattr(roteiro_api, "cancelar_passagens", cancelar_mock)

    def commit_que_falha():
        raise RuntimeError("falha simulada de banco")

    monkeypatch.setattr(session, "commit", commit_que_falha)

    resposta = client.post(f"/roteiros/{roteiro_id}/reservar")

    assert resposta.status_code == 500
    cancelar_mock.assert_awaited_once_with(roteiro_id)
