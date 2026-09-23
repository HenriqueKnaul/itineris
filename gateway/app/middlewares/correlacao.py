"""Middleware de rastreio: dá um ID único a cada requisição e mede o tempo."""
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("gateway")


class CorrelacaoMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())

        # headers do Starlette são imutáveis: mexe direto na lista de bytes do escopo
        request.scope["headers"] = [
            (chave, valor)
            for chave, valor in request.scope["headers"]
            if chave != b"x-request-id"
        ] + [(b"x-request-id", request_id.encode())]

        inicio = time.perf_counter()
        resposta = await call_next(request)
        duracao_ms = (time.perf_counter() - inicio) * 1000

        resposta.headers["x-request-id"] = request_id
        logger.info(
            "%s %s -> %s (%.1f ms) [%s]",
            request.method,
            request.url.path,
            resposta.status_code,
            duracao_ms,
            request_id,
        )
        return resposta
