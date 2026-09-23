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


