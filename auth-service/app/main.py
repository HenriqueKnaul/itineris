import hmac
import os
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException
from jose import jwt
from pydantic import BaseModel

# Mesma chave usada pelo gateway para validar o token (ver .env.example).
SECRET_KEY = os.getenv("SECRET_KEY", "chave-padrao-apenas-para-desenvolvimento-trocar-em-producao")
ALGORITHM = "HS256"
EXPIRACAO_MINUTOS = 120

# Sem banco: o único usuário vem da configuração (padrão: admin / admin).
USUARIOS = {
    "admin": {"nome": "Administrador", "senha": os.getenv("ADMIN_PASSWORD", "admin")},
}

app = FastAPI(title="Auth Service - Itineris")


class LoginIn(BaseModel):
    id: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


@app.get("/health")
def health():
    return {"status": "healthy", "service": "auth-service"}


@app.post("/auth/login", response_model=Token)
def login(dados: LoginIn):
    usuario = USUARIOS.get(dados.id)
    if not usuario or not hmac.compare_digest(dados.password, usuario["senha"]):
        raise HTTPException(status_code=401, detail="ID ou palavra-passe incorretos.")

    exp = datetime.now(timezone.utc) + timedelta(minutes=EXPIRACAO_MINUTOS)
    token = jwt.encode({"sub": dados.id, "nome": usuario["nome"], "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token}
