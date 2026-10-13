from datetime import date, timedelta

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


def test_reservar_aprova_roteiro(client):
    resposta = client.post("/cotacoes/reservar", json=_payload(teto=3000.0))

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "aprovado"
    assert corpo["valor_total"] == 2500.0
    assert corpo["saldo_restante"] == 500.0


def test_reservar_sem_saldo_rejeita(client):
    resposta = client.post("/cotacoes/reservar", json=_payload(teto=1000.0))

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "rejeitado"
    assert corpo["motivo"] == "sem_saldo"


def test_cancelar_reserva(client):
    client.post("/cotacoes/reservar", json=_payload())
    resposta = client.post("/cotacoes/cancelar", json={"roteiro_id": 1})

    assert resposta.status_code == 200
    assert resposta.json()["reservas_canceladas"] == 3


def test_consultar_extrato(client):
    client.post("/cotacoes/reservar", json=_payload(teto=3000.0))
    resposta = client.get("/orcamentos/1/extrato")

    assert resposta.status_code == 200
    assert resposta.json()["saldo"] == 500.0