"""Validação de tokens JWT no API Gateway.

O gateway é o único ponto de entrada do ecossistema, então é aqui que faz
sentido barrar requisições sem um token válido antes de repassá-las aos
microsserviços de domínio (roteiro-service e cotacao-service). O auth-service
continua sendo o único responsável por EMITIR o token (rota /auth/login);
o gateway só sabe conferir a assinatura.

A SECRET_KEY precisa ser a mesma usada pelo auth-service para assinar o
token — por isso ambos os serviços lêem a mesma variável de ambiente.
"""
import os

from jose import JWTError, jwt

SECRET_KEY = os.getenv("SECRET_KEY", "chave-padrao-apenas-para-desenvolvimento-trocar-em-producao")
ALGORITHM = "HS256"


class TokenInvalido(Exception):
    """O token está ausente, expirado, malformado ou com assinatura inválida."""


def validar_token(token: str) -> dict:
    """Decodifica e valida o token JWT. Levanta TokenInvalido se ele não passar."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as erro:
        raise TokenInvalido(str(erro)) from erro
