from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from app.database import create_db_and_tables
from app.roteiros import router as roteiros_router
import os

AMBIENTE = os.getenv("AMBIENTE", "DEV").upper() #variavel de ambiente para desligar swagger da homol como solicitado

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(
    title="Serviço de Roteiro - Itineris",
    description="Gestão de roteiros e destinos de viagem. Orquestra a Saga de reserva com o cotacao-service.",
    lifespan=lifespan,
    docs_url="/docs" if AMBIENTE == "DEV" else None,
    redoc_url="/redoc" if AMBIENTE == "DEV" else None,
    openapi_url="/openapi.json" if AMBIENTE == "DEV" else None,
)

Instrumentator().instrument(app).expose(app, tags=["Infra"])

app.include_router(roteiros_router)

@app.get("/health")
def health_check():
    return {"status": "healthy"}
