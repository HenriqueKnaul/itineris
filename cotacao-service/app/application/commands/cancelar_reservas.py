"""Comando: cancelar as reservas de um roteiro (compensação da Saga)."""
from sqlmodel import Session

from app.domain.models import StatusReserva
from app.infrastructure.write_model import repositorio


def cancelar_reservas(session: Session, roteiro_id: int) -> int:
    """Devolve vagas e valor ao orçamento. Retorna quantas reservas foram canceladas.

    Idempotente: se não há reservas confirmadas, não faz nada e retorna 0.
    """
    reservas = repositorio.listar_reservas_confirmadas(session, roteiro_id)
    if not reservas:
        return 0

    try:
        valor_devolvido = 0.0
        for reserva in reservas:
            voo = repositorio.buscar_voo(session, reserva.voo_id)
            voo.vagas = min(voo.vagas + 1, voo.capacidade)
            session.add(voo)

            reserva.status = StatusReserva.CANCELADA.value
            session.add(reserva)
            valor_devolvido += reserva.valor_cobrado

        orcamento = repositorio.buscar_orcamento(session, roteiro_id)
        if orcamento is not None:
            orcamento.valor_utilizado = max(
                0.0, round(orcamento.valor_utilizado - valor_devolvido, 2)
            )
            session.add(orcamento)

        session.commit()
    except Exception:
        session.rollback()
        raise

    return len(reservas)
