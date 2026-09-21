from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.infrastructure.database import create_db_and_tables
from app.api.auth import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Executa na inicialização do serviço
    create_db_and_tables()
    yield

app = FastAPI(
    title="Serviço de Autenticação - Itineris",
    description="Microsserviço de gestão de autenticação e tokens JWT.",
    lifespan=lifespan
)

app.include_router(auth_router)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "auth-service"}