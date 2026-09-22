"""Tabela de roteamento do API Gateway.

O gateway não conhece regra de negócio nenhuma: ele só sabe que o *primeiro
segmento* da URL indica qual microsserviço deve atender a requisição.

    /roteiros/1        -> roteiro-service
    /cotacoes/reservar -> cotacao-service

As URLs vêm de variáveis de ambiente para que o mesmo código rode dentro do
Docker (onde o host é o nome do serviço) e fora dele (localhost).
"""
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
    # Ainda não implementado pelo grupo; quando o auth-service subir, já roteia.
    "auth": AUTH_SERVICE,
}

# Serviços usados pelo health check agregado.
SERVICOS: list[Servico] = [ROTEIRO_SERVICE, COTACAO_SERVICE, AUTH_SERVICE]


def resolver(caminho: str) -> Servico | None:
    """Descobre o serviço responsável por um caminho. None = rota desconhecida.

    >>> resolver("cotacoes/reservar").nome
    'cotacao-service'
    """
    prefixo = caminho.strip("/").split("/", 1)[0].lower()
    return MAPA_DE_ROTAS.get(prefixo)
