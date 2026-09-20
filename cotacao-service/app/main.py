from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from app.api.cotacoes import router as cotacoes_router
from app.api.orcamentos import router as orcamentos_router
from app.infrastructure.database import create_db_and_tables, engine
from app.infrastructure.write_model.seed import seed_voos


@asynccontextmanager
async def lifespan(app: FastAPI):
    with Session(engine) as session:
        seed_voos(session)
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
