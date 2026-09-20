"""Testes do comando reservar_roteiro (regras + banco em memória)."""
import pytest
from sqlmodel import select

from app.application.commands.reservar_roteiro import reservar_roteiro
from app.domain.erros import SemSaldo, SemVagas, VooNaoEncontrado
from app.domain.models import Orcamento, Reserva


def _todas_reservas(session):
    return list(session.exec(select(Reserva)).all())


def test_aprova_quando_ha_dinheiro_sobrando(session, catalogo, novo_comando, hoje):
    resultado = reservar_roteiro(session, novo_comando(teto=3000.0), hoje=hoje)

    assert resultado.valor_total == 2500.0
    assert resultado.saldo_restante == 500.0
    assert [(r.origem, r.destino, r.valor) for r in resultado.reservas] == [
        ("Brasil", "Lisboa", 1000.0),
        ("Lisboa", "Paris", 500.0),
        ("Paris", "Brasil", 1000.0),
    ]


def test_aprovacao_consome_uma_vaga_por_trecho_e_registra_o_orcamento(
    session, catalogo, novo_comando, hoje
):
    reservar_roteiro(session, novo_comando(teto=3000.0), hoje=hoje)

    assert catalogo[("Brasil", "Lisboa")].vagas == 99
    assert catalogo[("Lisboa", "Paris")].vagas == 99
    assert catalogo[("Paris", "Brasil")].vagas == 99
    assert catalogo[("Paris", "Lisboa")].vagas == 100  # não usado
    orcamento = session.exec(select(Orcamento)).one()
    assert orcamento.teto_financeiro == 3000.0
    assert orcamento.valor_utilizado == 2500.0
    assert len(_todas_reservas(session)) == 3


def test_aprova_quando_o_total_e_igual_ao_teto(session, catalogo, novo_comando, hoje):
    resultado = reservar_roteiro(session, novo_comando(teto=2500.0), hoje=hoje)

    assert resultado.saldo_restante == 0.0


def test_rejeita_quando_o_orcamento_nao_e_suficiente(session, catalogo, novo_comando, hoje):
    with pytest.raises(SemSaldo) as info:
        reservar_roteiro(session, novo_comando(teto=2000.0), hoje=hoje)

    erro = info.value
    assert erro.motivo == "sem_saldo"
    assert erro.valor_minimo_necessario == 2500.0
    assert erro.valor_faltante == 500.0
    assert erro.teto_financeiro == 2000.0
    assert [t.valor for t in erro.trechos] == [1000.0, 500.0, 1000.0]


def test_rejeicao_por_saldo_nao_grava_nada(session, catalogo, novo_comando, hoje):
    with pytest.raises(SemSaldo):
        reservar_roteiro(session, novo_comando(teto=2000.0), hoje=hoje)

    assert catalogo[("Brasil", "Lisboa")].vagas == 100
    assert _todas_reservas(session) == []
    assert session.exec(select(Orcamento)).first() is None


def test_rejeita_voo_sem_vagas(session, catalogo, novo_comando, hoje):
    with pytest.raises(SemVagas) as info:
        reservar_roteiro(session, novo_comando(cidades=("Tóquio",)), hoje=hoje)

    assert info.value.motivo == "sem_vagas"
    assert (info.value.trecho.origem, info.value.trecho.destino) == ("Brasil", "Tóquio")


def test_rejeicao_por_falta_de_vaga_nao_consome_vagas_de_outros_trechos(
    session, catalogo, novo_comando, hoje
):
    catalogo[("Paris", "Brasil")].vagas = 0
    session.add(catalogo[("Paris", "Brasil")])
    session.commit()

    with pytest.raises(SemVagas):
        reservar_roteiro(session, novo_comando(), hoje=hoje)

    assert catalogo[("Brasil", "Lisboa")].vagas == 100
    assert catalogo[("Lisboa", "Paris")].vagas == 100
    assert _todas_reservas(session) == []


def test_rejeita_trecho_que_nao_existe_no_catalogo(session, catalogo, novo_comando, hoje):
    with pytest.raises(VooNaoEncontrado) as info:
        reservar_roteiro(session, novo_comando(cidades=("Marte",)), hoje=hoje)

    assert info.value.motivo == "voo_nao_encontrado"
    assert info.value.trecho.destino == "Marte"


def test_reconhece_cidade_sem_acento_e_em_minusculas(session, catalogo, novo_comando, hoje):
    catalogo[("Brasil", "Tóquio")].vagas = 5
    session.add(catalogo[("Brasil", "Tóquio")])
    session.commit()

    resultado = reservar_roteiro(session, novo_comando(teto=99999.0, cidades=("toquio",)), hoje=hoje)

    assert resultado.reservas[0].destino == "Tóquio"


def test_mesmo_voo_em_dois_trechos_exige_duas_vagas(session, catalogo, novo_comando, hoje):
    # Lisboa -> Paris aparece duas vezes neste roteiro; só há 1 vaga.
    catalogo[("Lisboa", "Paris")].vagas = 1
    session.add(catalogo[("Lisboa", "Paris")])
    session.commit()

    with pytest.raises(SemVagas) as info:
        reservar_roteiro(
            session, novo_comando(cidades=("Lisboa", "Paris", "Lisboa", "Paris")), hoje=hoje
        )

    assert (info.value.trecho.origem, info.value.trecho.destino) == ("Lisboa", "Paris")


def test_aplica_tarifa_dinamica_no_valor_cobrado(session, catalogo, novo_comando, hoje):
    catalogo[("Brasil", "Lisboa")].vagas = 20  # 80% ocupado -> +30%
    session.add(catalogo[("Brasil", "Lisboa")])
    session.commit()

    resultado = reservar_roteiro(session, novo_comando(teto=5000.0), hoje=hoje)

    assert resultado.reservas[0].valor == 1300.0
    assert resultado.valor_total == 2800.0


def test_repetir_a_reserva_e_idempotente(session, catalogo, novo_comando, hoje):
    primeira = reservar_roteiro(session, novo_comando(teto=3000.0), hoje=hoje)
    segunda = reservar_roteiro(session, novo_comando(teto=3000.0), hoje=hoje)

    assert [r.reserva_id for r in segunda.reservas] == [r.reserva_id for r in primeira.reservas]
    assert segunda.valor_total == 2500.0
    assert segunda.saldo_restante == 500.0
    assert catalogo[("Brasil", "Lisboa")].vagas == 99  # consumiu só uma vez
    assert len(_todas_reservas(session)) == 3
