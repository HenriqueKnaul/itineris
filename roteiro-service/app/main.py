from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.infrastructure.database import create_db_and_tables
from app.api.roteiro import router as roteiro_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(
    title="Serviço de Roteiro - Itineris",
    description="Microsserviço responsável pela gestão de roteiros e destinos de viagem.",
    lifespan=lifespan
)

app.include_router(roteiro_router)

@app.get("/health")
def health_check():
    return {"status": "healthy"}