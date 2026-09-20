"""Proxy reverso: repassa a requisição recebida para o microsserviço de destino.

Responsabilidades desta camada:
  1. remontar a URL de destino preservando caminho e query string;
  2. repassar método, cabeçalhos e corpo sem alterar o conteúdo;
  3. limpar cabeçalhos que não podem ser repassados (hop-by-hop);
  4. traduzir falhas de rede em códigos HTTP claros (502/503/504).
"""
import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, Response

from app.routing.rotas import Servico

# Cabeçalhos que valem apenas para a conexão atual (RFC 9110) e, por isso,
# não podem ser repassados adiante.
HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}

# O httpx já descomprime o corpo e recalcula o tamanho: repassar os valores
# antigos faria o cliente tentar descomprimir um corpo já em texto puro.
IGNORADOS_NA_RESPOSTA = HOP_BY_HOP | {"content-encoding", "content-length"}


def _headers_da_requisicao(request: Request) -> dict[str, str]:
    """Cabeçalhos do cliente, limpos e com os X-Forwarded-* do proxy."""
    headers = {
        chave: valor
        for chave, valor in request.headers.items()
        if chave.lower() not in HOP_BY_HOP and chave.lower() not in {"host", "content-length"}
    }
    cliente = request.client.host if request.client else "desconhecido"
    headers["x-forwarded-for"] = cliente
    headers["x-forwarded-proto"] = request.url.scheme
    headers["x-forwarded-host"] = request.headers.get("host", "")
    return headers


def _headers_da_resposta(resposta: httpx.Response, servico: Servico) -> dict[str, str]:
    """Cabeçalhos do serviço, limpos e com a origem identificada."""
    headers = {
        chave: valor
        for chave, valor in resposta.headers.items()
        if chave.lower() not in IGNORADOS_NA_RESPOSTA
    }
    # Redirecionamentos (ex.: o 307 de barra final do FastAPI) apontam para a
    # URL interna do container. Reescrevemos para o caminho relativo, senão o
    # navegador do usuário tentaria acessar "http://cotacao-service:8003/...".
    location = headers.get("location")
    if location and location.startswith(servico.base_url):
        headers["location"] = location[len(servico.base_url) :] or "/"

    headers["x-servico-de-origem"] = servico.nome
    return headers


async def encaminhar(
    request: Request,
    caminho: str,
    servico: Servico,
    cliente: httpx.AsyncClient,
) -> Response:
    """Executa a chamada ao microsserviço e devolve a resposta ao cliente."""
    url = httpx.URL(
        f"{servico.base_url}/{caminho.lstrip('/')}",
        query=request.url.query.encode("utf-8"),
    )

    requisicao = cliente.build_request(
        method=request.method,
        url=url,
        headers=_headers_da_requisicao(request),
        content=await request.body(),
    )

    try:
        resposta = await cliente.send(requisicao)
    except httpx.ConnectError:
        return JSONResponse(
            status_code=503,
            content={
                "erro": "servico_indisponivel",
                "mensagem": f"O serviço '{servico.nome}' não está no ar.",
                "servico": servico.nome,
            },
        )
    except httpx.TimeoutException:
        return JSONResponse(
            status_code=504,
            content={
                "erro": "tempo_esgotado",
                "mensagem": f"O serviço '{servico.nome}' demorou demais para responder.",
                "servico": servico.nome,
            },
        )
    except httpx.RequestError as erro:
        return JSONResponse(
            status_code=502,
            content={
                "erro": "falha_de_comunicacao",
                "mensagem": f"Falha ao falar com '{servico.nome}': {erro.__class__.__name__}",
                "servico": servico.nome,
            },
        )

    return Response(
        content=resposta.content,
        status_code=resposta.status_code,
        headers=_headers_da_resposta(resposta, servico),
        media_type=resposta.headers.get("content-type"),
    )
