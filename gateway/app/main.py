"""API Gateway do Itineris: ponto de entrada único, roteia por prefixo de URL."""
import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.core import seguranca
from app.middlewares.correlacao import CorrelacaoMiddleware
from app.routing import proxy
from app.routing.rotas import MAPA_DE_ROTAS, SERVICOS, Servico, resolver

# login não exige token; o resto passa pela validação do JWT
PREFIXOS_PUBLICOS = {"auth"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

METODOS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]

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


def _autenticar(request: Request) -> JSONResponse | None:
    """Confere o header Authorization. Devolve uma resposta 401 se algo estiver errado, senão None."""
    cabecalho = request.headers.get("authorization", "")
    if not cabecalho.lower().startswith("bearer "):
        return JSONResponse(
            status_code=401,
            content={
                "erro": "nao_autenticado",
                "mensagem": "Cabeçalho Authorization ausente. Use 'Authorization: Bearer <token>'.",
            },
        )

    token = cabecalho[len("bearer ") :].strip()
    try:
        seguranca.validar_token(token)
    except seguranca.TokenInvalido as erro:
        return JSONResponse(
            status_code=401,
            content={"erro": "token_invalido", "mensagem": str(erro)},
        )
    return None


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

    prefixo = caminho.strip("/").split("/", 1)[0].lower()
    if prefixo not in PREFIXOS_PUBLICOS:
        resposta_de_erro = _autenticar(request)
        if resposta_de_erro is not None:
            return resposta_de_erro

    return await proxy.encaminhar(request, caminho, servico, request.app.state.cliente)
