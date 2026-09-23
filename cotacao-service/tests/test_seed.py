"""Testes da carga inicial do catálogo."""
from sqlmodel import select

from app.models import Voo
from app.seed import VOOS_INICIAIS, seed_voos


def test_seed_insere_o_catalogo_completo(session):
    assert seed_voos(session) == len(VOOS_INICIAIS)
    assert len(session.exec(select(Voo)).all()) == len(VOOS_INICIAIS)


def test_seed_e_idempotente(session):
    seed_voos(session)

    assert seed_voos(session) == 0
    assert len(session.exec(select(Voo)).all()) == len(VOOS_INICIAIS)


def test_seed_completa_apenas_rotas_que_faltam(session):
    session.add(Voo(origem="Brasil", destino="Lisboa", preco_base=1.0, capacidade=1, vagas=1))
    session.commit()

    assert seed_voos(session) == len(VOOS_INICIAIS) - 1


def test_seed_tem_voo_de_volta_para_cada_destino():
    ida = {d for o, d, *_ in VOOS_INICIAIS if o == "Brasil"}
    volta = {o for o, d, *_ in VOOS_INICIAIS if d == "Brasil"}

    assert ida <= volta
