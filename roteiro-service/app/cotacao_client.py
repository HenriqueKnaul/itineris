"""Cliente HTTP para falar com o cotacao-service."""
import os

import httpx

COTACAO_SERVICE_URL = os.getenv("COTACAO_SERVICE_URL", "http://cotacao-service:8003")
TIMEOUT = httpx.Timeout(connect=3.0, read=10.0, write=10.0, pool=3.0)


class FalhaDeComunicacao(Exception):
    """O cotacao-service não respondeu (fora do ar, timeout ou erro interno)."""


async def reservar_passagens(roteiro_id: int, teto_financeiro: float, destinos: list) -> dict:
    """Pede a reserva. A resposta tem status 'aprovado' ou 'rejeitado' (com o motivo)."""
    corpo = {
        "roteiro_id": roteiro_id,
        "teto_financeiro": teto_financeiro,
        "destinos": [
            {
                "cidade": d.cidade,
                "data_chegada": d.data_chegada.isoformat(),
                "data_partida": d.data_partida.isoformat(),
            }
            for d in destinos
        ],
    }
    return await _post("/cotacoes/reservar", corpo)


async def cancelar_passagens(roteiro_id: int) -> int:
    """Cancela as reservas do roteiro. Retorna quantas foram canceladas."""
    resposta = await _post("/cotacoes/cancelar", {"roteiro_id": roteiro_id})
    return resposta.get("reservas_canceladas", 0)


async def _post(caminho: str, corpo: dict) -> dict:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as cliente:
            resposta = await cliente.post(f"{COTACAO_SERVICE_URL}{caminho}", json=corpo)
    except httpx.RequestError as erro:
        raise FalhaDeComunicacao(f"Não foi possível falar com o cotacao-service: {erro.__class__.__name__}") from erro

    if resposta.status_code >= 500:
        raise FalhaDeComunicacao(f"cotacao-service respondeu com erro interno ({resposta.status_code}).")

    return resposta.json()
