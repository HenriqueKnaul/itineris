"""Validação de tokens JWT no API Gateway."""
import os

from jose import JWTError, jwt

SECRET_KEY = os.getenv("SECRET_KEY", "chave-padrao-apenas-para-desenvolvimento-trocar-em-producao")  # mesma chave do auth-service
ALGORITHM = "HS256"


class TokenInvalido(Exception):
    """O token está ausente, expirado, malformado ou com assinatura inválida."""


def validar_token(token: str) -> dict:
    """Decodifica e valida o token JWT. Levanta TokenInvalido se ele não passar."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as erro:
        raise TokenInvalido(str(erro)) from erro
