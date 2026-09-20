"""API Gateway do Itineris — ponto de entrada único do ecossistema.

Padrão de microsserviços: **API Gateway**. O cliente conhece apenas a porta
8000; o gateway descobre o serviço de destino pelo prefixo da URL e repassa a
chamada (proxy reverso) usando `httpx`.

    /roteiros/*, /destinos/*    -> roteiro-service  (8002)
    /cotacoes/*, /orcamentos/*  -> cotacao-service  (8003)
    /auth/*                     -> auth-service     (8001)
"""
import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.middlewares.correlacao import CorrelacaoMiddleware
from app.routing import proxy
from app.routing.rotas import MAPA_DE_ROTAS, SERVICOS, Servico, resolver

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

METODOS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]

# Um único cliente HTTP para todo o processo: reaproveitar as conexões TCP é o
# que mantém o gateway leve mesmo sendo o caminho de todo o tráfego.
TEMPO_LIMITE = httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=5.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.cliente = httpx.AsyncClient(
        timeout=TEMPO_LIMITE,
        follow_redirects=False,  # o redirecionamento é decisão do cliente final
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    )
    yield
    await app.state.cliente.aclose()


app = FastAPI(
    title="API Gateway - Itineris",
    description="Ponto de entrada único: roteia o tráfego para os microsserviços de domínio.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(CorrelacaoMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # projeto acadêmico; em produção, restringir
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Rotas do próprio gateway (registradas ANTES do catch-all) ---------------
@app.get("/", tags=["Gateway"], summary="Mapa de roteamento")
def raiz():
    return {
        "servico": "api-gateway",
        "rotas": {f"/{prefixo}": servico.nome for prefixo, servico in MAPA_DE_ROTAS.items()},
    }


@app.get("/health", tags=["Gateway"], summary="Saúde do próprio gateway")
def health():
    return {"status": "healthy"}


@app.get("/health/servicos", tags=["Gateway"], summary="Saúde dos serviços de domínio")
async def health_servicos(request: Request):
    """Consulta o /health de cada microsserviço em paralelo."""
    cliente: httpx.AsyncClient = request.app.state.cliente

    async def checar(servico: Servico) -> tuple[str, str]:
        try:
            resposta = await cliente.get(f"{servico.base_url}/health", timeout=3.0)
            return servico.nome, "healthy" if resposta.status_code == 200 else "degradado"
        except httpx.RequestError:
            return servico.nome, "indisponivel"

    resultados = dict(await asyncio.gather(*(checar(s) for s in SERVICOS)))
    todos_ok = all(estado == "healthy" for estado in resultados.values())
    return JSONResponse(
        status_code=200 if todos_ok else 503,
        content={"status": "healthy" if todos_ok else "degradado", "servicos": resultados},
    )


# --- Catch-all: tudo que não for do gateway vira proxy ----------------------
@app.api_route("/{caminho:path}", methods=METODOS, include_in_schema=False)
async def encaminhar(caminho: str, request: Request) -> Response:
    servico = resolver(caminho)
    if servico is None:
        return JSONResponse(
            status_code=404,
            content={
                "erro": "rota_nao_mapeada",
                "mensagem": f"Nenhum microsserviço responde por '/{caminho}'.",
                "rotas_disponiveis": sorted(f"/{p}" for p in MAPA_DE_ROTAS),
            },
        )
    return await proxy.encaminhar(request, caminho, servico, request.app.state.cliente)
