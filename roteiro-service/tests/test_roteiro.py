"""Testes de integração das rotas de roteiro (FastAPI TestClient + banco em memória).

Foco: CRUD, validação de datas, cascade delete e a Saga de reserva, incluindo a
compensação quando o commit local falha depois da aprovação remota.
O cotacao-service é sempre simulado (AsyncMock): aqui só testamos o roteiro-service.
"""
from unittest.mock import AsyncMock

import pytest
from sqlmodel import select

import app.roteiros as roteiros
from app.models import Destino

APROVADO = {
    "status": "aprovado",
    "valor_total": 1000.0,
    "saldo_restante": 4000.0,
    "reservas": [{"reserva_id": 1, "origem": "Brasil", "destino": "Lisboa"}],
}


@pytest.fixture
def roteiro_id(client, payload_roteiro):
    return client.post("/roteiros/", json=payload_roteiro).json()["id"]


# ---------- CRUD ----------
def test_criar_roteiro_com_destinos(client, payload_roteiro, session):
    resposta = client.post("/roteiros/", json=payload_roteiro)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["titulo"] == "Férias na Europa"
    assert corpo["status"] == "RASCUNHO"
    destinos = session.exec(select(Destino).where(Destino.roteiro_id == corpo["id"])).all()
    assert len(destinos) == 1
    assert destinos[0].cidade == "Lisboa"


def test_data_fim_antes_da_data_inicio_e_rejeitada(client, payload_roteiro):
    payload_roteiro["data_fim"] = "2000-01-01"

    assert client.post("/roteiros/", json=payload_roteiro).status_code == 422


def test_deletar_roteiro_remove_os_destinos_em_cascata(client, roteiro_id, session):
    resposta = client.delete(f"/roteiros/{roteiro_id}")

    assert resposta.status_code == 204
    assert client.get(f"/roteiros/{roteiro_id}").status_code == 404
    assert session.get(Destino, 1) is None  # sem o cascade, o destino ficaria órfão


def test_roteiro_inexistente_da_404(client):
    assert client.get("/roteiros/999").status_code == 404


# ---------- Saga ----------
def test_reservar_aprovado_marca_o_roteiro_como_reservado(client, roteiro_id, monkeypatch):
    monkeypatch.setattr(roteiros, "reservar_passagens", AsyncMock(return_value=APROVADO))

    resposta = client.post(f"/roteiros/{roteiro_id}/reservar")

    assert resposta.status_code == 200
    assert resposta.json()["status_roteiro"] == "RESERVADO"
    assert client.get(f"/roteiros/{roteiro_id}").json()["status"] == "RESERVADO"


def test_reservar_rejeitado_devolve_422_e_nao_muda_o_status(client, roteiro_id, monkeypatch):
    rejeitado = {"status": "rejeitado", "motivo": "sem_saldo", "mensagem": "Sem saldo."}
    monkeypatch.setattr(roteiros, "reservar_passagens", AsyncMock(return_value=rejeitado))

    resposta = client.post(f"/roteiros/{roteiro_id}/reservar")

    assert resposta.status_code == 422
    assert resposta.json()["detail"]["motivo"] == "sem_saldo"
    assert client.get(f"/roteiros/{roteiro_id}").json()["status"] == "RASCUNHO"


def test_reservar_com_cotacao_fora_do_ar_devolve_503(client, roteiro_id, monkeypatch):
    erro = AsyncMock(side_effect=roteiros.FalhaDeComunicacao("fora do ar"))
    monkeypatch.setattr(roteiros, "reservar_passagens", erro)

    assert client.post(f"/roteiros/{roteiro_id}/reservar").status_code == 503


def test_reservar_duas_vezes_da_409(client, roteiro_id, monkeypatch):
    monkeypatch.setattr(roteiros, "reservar_passagens", AsyncMock(return_value=APROVADO))
    client.post(f"/roteiros/{roteiro_id}/reservar")

    assert client.post(f"/roteiros/{roteiro_id}/reservar").status_code == 409


def test_reservar_roteiro_compensa_quando_commit_local_falha(client, roteiro_id, session, monkeypatch):
    """Aprova a reserva no cotacao-service, mas força o commit local a falhar: a rota
    precisa acionar a compensação (cancelar_passagens) em vez de deixar os dois bancos
    inconsistentes."""
    monkeypatch.setattr(roteiros, "reservar_passagens", AsyncMock(return_value=APROVADO))
    cancelar_mock = AsyncMock(return_value=1)
    monkeypatch.setattr(roteiros, "cancelar_passagens", cancelar_mock)

    def commit_que_falha():
        raise RuntimeError("falha simulada de banco")

    monkeypatch.setattr(session, "commit", commit_que_falha)

    resposta = client.post(f"/roteiros/{roteiro_id}/reservar")

    assert resposta.status_code == 500
    cancelar_mock.assert_awaited_once_with(roteiro_id)


def test_cancelar_reserva_marca_o_roteiro_como_cancelado(client, roteiro_id, monkeypatch):
    monkeypatch.setattr(roteiros, "reservar_passagens", AsyncMock(return_value=APROVADO))
    monkeypatch.setattr(roteiros, "cancelar_passagens", AsyncMock(return_value=3))
    client.post(f"/roteiros/{roteiro_id}/reservar")

    resposta = client.post(f"/roteiros/{roteiro_id}/cancelar-reserva")

    assert resposta.json() == {"roteiro_id": roteiro_id, "status_roteiro": "CANCELADO", "reservas_canceladas": 3}


def test_cancelar_reserva_de_roteiro_nao_reservado_da_409(client, roteiro_id):
    assert client.post(f"/roteiros/{roteiro_id}/cancelar-reserva").status_code == 409
