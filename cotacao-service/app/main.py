from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import create_db_and_tables
from app.escrita import router as escrita_router
from app.leitura import router as leitura_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Serviço de Cotação - Itineris",
    description="Orçamento e reserva de passagens (CQRS: escrita.py e leitura.py).",
    lifespan=lifespan,
)

app.include_router(escrita_router)
app.include_router(leitura_router)


@app.get("/health", tags=["Infra"])
def health_check():
    return {"status": "healthy"}
