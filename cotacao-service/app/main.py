from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.cotacoes import router as cotacoes_router
from app.api.orcamentos import router as orcamentos_router
from app.infrastructure.database import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create_db_and_tables() cria o schema e já popula os voos iniciais
    # (seed_voos é idempotente: não duplica se rodar de novo).
    create_db_and_tables()
    yield


app = FastAPI(
    title="Serviço de Cotação - Itineris",
    description=(
        "Microsserviço responsável pelo orçamento e pela reserva de passagens "
        "(CQRS: comandos e consultas separados)."
    ),
    lifespan=lifespan,
)

app.include_router(cotacoes_router)
app.include_router(orcamentos_router)


@app.get("/health", tags=["Infra"])
def health_check():
    return {"status": "healthy"}
