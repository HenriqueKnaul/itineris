"""Testes das rotas HTTP (FastAPI TestClient + banco em memória)."""
from datetime import date, timedelta

# Datas a mais de 7 dias de hoje: a tarifa não recebe acréscimo de última hora.
CHEGADA = date.today() + timedelta(days=60)


def _payload(cidades=("Lisboa", "Paris"), teto=3000.0, roteiro_id=1):
    destinos = []
    for i, cidade in enumerate(cidades):
        chegada = CHEGADA + timedelta(days=5 * i)
        destinos.append(
            {
                "cidade": cidade,
                "data_chegada": chegada.isoformat(),
                "data_partida": (chegada + timedelta(days=5)).isoformat(),
            }
        )
    return {"roteiro_id": roteiro_id, "teto_financeiro": teto, "destinos": destinos}


def test_health(client):
    resposta = client.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "healthy"}


def test_reservar_aprova_e_devolve_os_trechos(client):
    resposta = client.post("/cotacoes/reservar", json=_payload(teto=3000.0))

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "aprovado"
    assert corpo["valor_total"] == 2500.0
    assert corpo["saldo_restante"] == 500.0
    assert len(corpo["reservas"]) == 3


def test_reservar_sem_saldo_devolve_200_com_status_rejeitado(client):
    resposta = client.post("/cotacoes/reservar", json=_payload(teto=1000.0))

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "rejeitado"
    assert corpo["motivo"] == "sem_saldo"
    assert corpo["valor_faltante"] == 1500.0
    assert len(corpo["trechos"]) == 3
    assert "trecho" not in corpo  # campos vazios não aparecem


def test_reservar_voo_inexistente_devolve_o_trecho(client):
    resposta = client.post("/cotacoes/reservar", json=_payload(cidades=("Marte",)))

    corpo = resposta.json()
    assert corpo["status"] == "rejeitado"
    assert corpo["motivo"] == "voo_nao_encontrado"
    assert corpo["trecho"]["destino"] == "Marte"


def test_cancelar_devolve_quantas_reservas_foram_canceladas(client):
    client.post("/cotacoes/reservar", json=_payload())

    resposta = client.post("/cotacoes/cancelar", json={"roteiro_id": 1})

    assert resposta.json() == {"status": "cancelado", "reservas_canceladas": 3}


def test_extrato_devolve_saldo_e_passagens(client):
    client.post("/cotacoes/reservar", json=_payload(teto=3000.0))

    resposta = client.get("/orcamentos/1/extrato")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["saldo"] == 500.0
    assert len(corpo["passagens"]) == 3


def test_extrato_de_roteiro_sem_orcamento_da_404(client):
    assert client.get("/orcamentos/999/extrato").status_code == 404
