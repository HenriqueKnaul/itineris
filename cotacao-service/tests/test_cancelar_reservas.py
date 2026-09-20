"""Testes da compensação da Saga (cancelar_reservas) e do extrato."""
from sqlmodel import select

from app.application.commands.cancelar_reservas import cancelar_reservas
from app.application.commands.reservar_roteiro import reservar_roteiro
from app.application.queries.consultar_extrato import consultar_extrato
from app.domain.models import Orcamento, Reserva, StatusReserva


def test_cancelar_devolve_vagas_e_valor(session, catalogo, novo_comando, hoje):
    reservar_roteiro(session, novo_comando(teto=3000.0), hoje=hoje)

    cancelados = cancelar_reservas(session, roteiro_id=1)

    assert cancelados == 3
    assert catalogo[("Brasil", "Lisboa")].vagas == 100
    assert catalogo[("Lisboa", "Paris")].vagas == 100
    assert catalogo[("Paris", "Brasil")].vagas == 100
    assert session.exec(select(Orcamento)).one().valor_utilizado == 0.0
    status = {r.status for r in session.exec(select(Reserva)).all()}
    assert status == {StatusReserva.CANCELADA.value}


def test_cancelar_duas_vezes_nao_devolve_em_dobro(session, catalogo, novo_comando, hoje):
    reservar_roteiro(session, novo_comando(teto=3000.0), hoje=hoje)
    cancelar_reservas(session, roteiro_id=1)

    segunda = cancelar_reservas(session, roteiro_id=1)

    assert segunda == 0
    assert catalogo[("Brasil", "Lisboa")].vagas == 100


def test_cancelar_roteiro_sem_reservas_retorna_zero(session, catalogo):
    assert cancelar_reservas(session, roteiro_id=999) == 0


def test_da_para_reservar_novamente_depois_de_cancelar(session, catalogo, novo_comando, hoje):
    reservar_roteiro(session, novo_comando(teto=3000.0), hoje=hoje)
    cancelar_reservas(session, roteiro_id=1)

    resultado = reservar_roteiro(session, novo_comando(teto=4000.0), hoje=hoje)

    assert resultado.valor_total == 2500.0
    assert resultado.saldo_restante == 1500.0
    assert catalogo[("Brasil", "Lisboa")].vagas == 99
    assert session.exec(select(Orcamento)).one().teto_financeiro == 4000.0


# ---------- Extrato (query) ----------
def test_extrato_de_roteiro_sem_orcamento_e_none(session, catalogo):
    assert consultar_extrato(session, roteiro_id=42) is None


def test_extrato_mostra_saldo_e_passagens(session, catalogo, novo_comando, hoje):
    reservar_roteiro(session, novo_comando(teto=3000.0), hoje=hoje)

    extrato = consultar_extrato(session, roteiro_id=1)

    assert extrato.teto_financeiro == 3000.0
    assert extrato.valor_utilizado == 2500.0
    assert extrato.saldo == 500.0
    assert [(p.origem, p.destino, p.valor, p.status) for p in extrato.passagens] == [
        ("Brasil", "Lisboa", 1000.0, "CONFIRMADA"),
        ("Lisboa", "Paris", 500.0, "CONFIRMADA"),
        ("Paris", "Brasil", 1000.0, "CONFIRMADA"),
    ]


def test_extrato_apos_cancelamento_mostra_saldo_integral(session, catalogo, novo_comando, hoje):
    reservar_roteiro(session, novo_comando(teto=3000.0), hoje=hoje)
    cancelar_reservas(session, roteiro_id=1)

    extrato = consultar_extrato(session, roteiro_id=1)

    assert extrato.saldo == 3000.0
    assert {p.status for p in extrato.passagens} == {"CANCELADA"}
