"""Testes de integração das rotas HTTP (FastAPI TestClient + banco em memória)."""
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


def test_reservar_aprovado(client):
    resposta = client.post("/cotacoes/reservar", json=_payload(teto=3000.0))

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "aprovado"
    assert corpo["valor_total"] == 2500.0
    assert corpo["saldo_restante"] == 500.0
    assert [(r["origem"], r["destino"]) for r in corpo["reservas"]] == [
        ("Brasil", "Lisboa"),
        ("Lisboa", "Paris"),
        ("Paris", "Brasil"),
    ]


def test_reservar_sem_saldo_informa_o_minimo_necessario(client):
    resposta = client.post("/cotacoes/reservar", json=_payload(teto=2000.0))

    assert resposta.status_code == 200  # rejeição de negócio não é erro HTTP
    corpo = resposta.json()
    assert corpo["status"] == "rejeitado"
    assert corpo["motivo"] == "sem_saldo"
    assert corpo["teto_financeiro"] == 2000.0
    assert corpo["valor_minimo_necessario"] == 2500.0
    assert corpo["valor_faltante"] == 500.0
    assert len(corpo["trechos"]) == 3
    assert "trecho" not in corpo


def test_reservar_sem_vagas(client):
    resposta = client.post("/cotacoes/reservar", json=_payload(cidades=("Tóquio",)))

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "rejeitado"
    assert corpo["motivo"] == "sem_vagas"
    assert corpo["trecho"]["origem"] == "Brasil"
    assert corpo["trecho"]["destino"] == "Tóquio"
    assert "valor" not in corpo["trecho"]


def test_reservar_voo_inexistente(client):
    resposta = client.post("/cotacoes/reservar", json=_payload(cidades=("Marte",)))

    assert resposta.status_code == 200
    assert resposta.json()["motivo"] == "voo_nao_encontrado"


def test_reservar_sem_destinos_retorna_422(client):
    payload = _payload()
    payload["destinos"] = []

    assert client.post("/cotacoes/reservar", json=payload).status_code == 422


def test_reservar_com_partida_antes_da_chegada_retorna_422(client):
    payload = _payload(cidades=("Lisboa",))
    payload["destinos"][0]["data_partida"] = (CHEGADA - timedelta(days=1)).isoformat()

    assert client.post("/cotacoes/reservar", json=payload).status_code == 422


def test_reservar_com_teto_negativo_retorna_422(client):
    assert client.post("/cotacoes/reservar", json=_payload(teto=-1)).status_code == 422


def test_cancelar_compensa_a_reserva(client):
    client.post("/cotacoes/reservar", json=_payload(teto=3000.0))

    resposta = client.post("/cotacoes/cancelar", json={"roteiro_id": 1})

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "cancelado", "reservas_canceladas": 3}
    repetida = client.post("/cotacoes/cancelar", json={"roteiro_id": 1})
    assert repetida.json()["reservas_canceladas"] == 0


def test_extrato_de_roteiro_inexistente_retorna_404(client):
    assert client.get("/orcamentos/999/extrato").status_code == 404


def test_extrato_mostra_saldo_e_passagens(client):
    client.post("/cotacoes/reservar", json=_payload(teto=3000.0))

    resposta = client.get("/orcamentos/1/extrato")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["teto_financeiro"] == 3000.0
    assert corpo["valor_utilizado"] == 2500.0
    assert corpo["saldo"] == 500.0
    assert len(corpo["passagens"]) == 3
    assert corpo["passagens"][0]["status"] == "CONFIRMADA"
