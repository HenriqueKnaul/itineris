from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import create_db_and_tables
from app.roteiros import router as roteiros_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Serviço de Roteiro - Itineris",
    description="Gestão de roteiros e destinos de viagem. Orquestra a Saga de reserva com o cotacao-service.",
    lifespan=lifespan,
)

app.include_router(roteiros_router)


@app.get("/health")
def health_check():
    return {"status": "healthy"}
