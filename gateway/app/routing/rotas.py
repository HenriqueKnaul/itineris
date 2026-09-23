"""Tabela de roteamento do API Gateway: primeiro segmento da URL -> microsserviço."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Servico:
    """Um microsserviço de destino conhecido pelo gateway."""

    nome: str
    base_url: str


ROTEIRO_SERVICE = Servico(
    nome="roteiro-service",
    base_url=os.getenv("ROTEIRO_SERVICE_URL", "http://roteiro-service:8002"),
)

COTACAO_SERVICE = Servico(
    nome="cotacao-service",
    base_url=os.getenv("COTACAO_SERVICE_URL", "http://cotacao-service:8003"),
)

AUTH_SERVICE = Servico(
    nome="auth-service",
    base_url=os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001"),
)


# prefixo (primeiro segmento da URL, sem a barra) -> serviço de destino
MAPA_DE_ROTAS: dict[str, Servico] = {
    "roteiros": ROTEIRO_SERVICE,
    "destinos": ROTEIRO_SERVICE,
    "cotacoes": COTACAO_SERVICE,
    "orcamentos": COTACAO_SERVICE,
    "auth": AUTH_SERVICE,
}

SERVICOS: list[Servico] = [ROTEIRO_SERVICE, COTACAO_SERVICE, AUTH_SERVICE]


def resolver(caminho: str) -> Servico | None:
    """Descobre o serviço responsável por um caminho. None = rota desconhecida."""
    prefixo = caminho.strip("/").split("/", 1)[0].lower()
    return MAPA_DE_ROTAS.get(prefixo)
