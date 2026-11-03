import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.database import create_db_and_tables
from app.escrita import router as escrita_router
from app.leitura import router as leitura_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

AMBIENTE = os.getenv("ENV", "DEV").upper()
mostrar_docs = None if AMBIENTE == "HOMOL" else "/docs"
mostrar_redoc = None if AMBIENTE == "HOMOL" else "/redoc"

app = FastAPI(
    title="Serviço de Cotação - Itineris",
    description="Orçamento e reserva de passagens",
    version="1.0.0",
    docs_url=mostrar_docs,
    redoc_url=mostrar_redoc,
    lifespan=lifespan,
)

Instrumentator().instrument(app).expose(app, tags=["Infra"])

app.include_router(escrita_router)
app.include_router(leitura_router)


@app.get("/health", tags=["Infra"])
def health_check():
    return {"status": "healthy"}