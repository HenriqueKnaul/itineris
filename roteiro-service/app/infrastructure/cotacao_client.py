"""Cliente HTTP para o cotacao-service."""
import os
from datetime import date

import httpx
from pydantic import BaseModel

COTACAO_SERVICE_URL = os.getenv("COTACAO_SERVICE_URL", "http://cotacao-service:8003")

_TIMEOUT = httpx.Timeout(connect=3.0, read=10.0, write=10.0, pool=3.0)


class FalhaDeComunicacao(Exception):
    """O cotacao-service não pôde ser alcançado (fora do ar ou timeout)."""


class ReservaAprovada(BaseModel):
    status: str
    valor_total: float
    saldo_restante: float
    reservas: list[dict]


class ReservaRejeitada(BaseModel):
    status: str
    motivo: str
    mensagem: str
    teto_financeiro: float | None = None
    valor_minimo_necessario: float | None = None
    valor_faltante: float | None = None
    trechos: list[dict] | None = None
    trecho: dict | None = None


async def reservar_passagens(
    roteiro_id: int,
    teto_financeiro: float,
    destinos: list[dict],
) -> ReservaAprovada | ReservaRejeitada:
    """Pede ao cotacao-service que reserve as passagens do roteiro."""
    corpo = {
        "roteiro_id": roteiro_id,
        "teto_financeiro": teto_financeiro,
        "destinos": [_serializar_datas(d) for d in destinos],
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as cliente:
        try:
            resposta = await cliente.post(f"{COTACAO_SERVICE_URL}/cotacoes/reservar", json=corpo)
        except httpx.RequestError as erro:
            raise FalhaDeComunicacao(
                f"Não foi possível falar com o cotacao-service: {erro.__class__.__name__}"
            ) from erro

    if resposta.status_code >= 500:
        raise FalhaDeComunicacao(
            f"cotacao-service respondeu com erro interno ({resposta.status_code})."
        )

    dados = resposta.json()
    if dados.get("status") == "aprovado":
        return ReservaAprovada(**dados)
    return ReservaRejeitada(**dados)


async def cancelar_passagens(roteiro_id: int) -> int:
    """Cancela as reservas do roteiro. Retorna quantas foram canceladas."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as cliente:
        try:
            resposta = await cliente.post(
                f"{COTACAO_SERVICE_URL}/cotacoes/cancelar",
                json={"roteiro_id": roteiro_id},
            )
        except httpx.RequestError as erro:
            raise FalhaDeComunicacao(
                f"Não foi possível falar com o cotacao-service: {erro.__class__.__name__}"
            ) from erro

    if resposta.status_code >= 500:
        raise FalhaDeComunicacao(
            f"cotacao-service respondeu com erro interno ({resposta.status_code})."
        )

    return resposta.json().get("reservas_canceladas", 0)


def _serializar_datas(destino: dict) -> dict:
    """Converte date -> "YYYY-MM-DD" para o corpo JSON (datas não são serializáveis por padrão)."""
    return {
        chave: (valor.isoformat() if isinstance(valor, date) else valor)
        for chave, valor in destino.items()
    }
