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

# Registra as rotas de Roteiros na aplicação
app.include_router(roteiro_router)

#@app.get("/")
#def home():
 #   return {"status": "Serviço de Roteiro e Banco de Dados operacionais!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}