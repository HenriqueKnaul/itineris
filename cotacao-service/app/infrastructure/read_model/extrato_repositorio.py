"""Acesso a dados do lado de LEITURA (usado pelas queries).

Só faz SELECT: nunca adiciona, altera nem faz commit.
"""
from typing import Optional

from sqlmodel import Session, select

from app.domain.models import Orcamento, Reserva, Voo


def buscar_orcamento(session: Session, roteiro_id: int) -> Optional[Orcamento]:
    return session.exec(
        select(Orcamento).where(Orcamento.roteiro_id == roteiro_id)
    ).first()


def listar_passagens(session: Session, roteiro_id: int) -> list[tuple[Reserva, Voo]]:
    linhas = session.exec(
        select(Reserva, Voo)
        .join(Voo, Voo.id == Reserva.voo_id)
        .where(Reserva.roteiro_id == roteiro_id)
        .order_by(Reserva.id)
    ).all()
    return [(reserva, voo) for reserva, voo in linhas]
