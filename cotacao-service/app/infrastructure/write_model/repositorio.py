"""Acesso a dados do lado de ESCRITA (usado pelos comandos)."""
from typing import Optional

from sqlmodel import Session, select

from app.domain.models import Orcamento, Reserva, StatusReserva, Voo


def listar_voos(session: Session) -> list[Voo]:
    # O catálogo é pequeno e fictício; carregá-lo inteiro permite comparar
    # nomes de cidade normalizados (sem acento/caixa) em Python.
    return list(session.exec(select(Voo)).all())


def buscar_voo(session: Session, voo_id: int) -> Optional[Voo]:
    return session.get(Voo, voo_id)


def buscar_orcamento(session: Session, roteiro_id: int) -> Optional[Orcamento]:
    return session.exec(
        select(Orcamento).where(Orcamento.roteiro_id == roteiro_id)
    ).first()


def listar_reservas_confirmadas(session: Session, roteiro_id: int) -> list[Reserva]:
    return list(
        session.exec(
            select(Reserva)
            .where(
                Reserva.roteiro_id == roteiro_id,
                Reserva.status == StatusReserva.CONFIRMADA.value,
            )
            .order_by(Reserva.id)
        ).all()
    )
