"""Testes do API Gateway.

Cobertura deliberadamente parcial: por enquanto so os modulos de seguranca
e de roteamento tem testes proprios (unitarios, sem subir o TestClient). A
rota HTTP em si (app/main.py) e o proxy reverso (app/routing/proxy.py) ainda
nao tem testes automatizados.
"""
from app.core.seguranca import TokenInvalido, validar_token
from app.routing.rotas import resolver


def test_seguranca_validar_token_aceita_token_valido(token_valido):
    payload = validar_token(token_valido)

    assert payload["sub"] == "admin"


def test_seguranca_validar_token_rejeita_token_invalido():
    try:
        validar_token("isto-nao-e-um-jwt")
        assert False, "deveria ter levantado TokenInvalido"
    except TokenInvalido:
        pass


def test_resolver_encontra_o_servico_pelo_prefixo():
    servico = resolver("cotacoes/reservar")

    assert servico.nome == "cotacao-service"


def test_resolver_retorna_none_para_prefixo_desconhecido():
    assert resolver("isso-nao-existe/123") is None
