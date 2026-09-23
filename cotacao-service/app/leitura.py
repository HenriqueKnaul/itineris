"""CQRS - lado de LEITURA (consultas): só faz SELECT, nunca altera nada.

As rotas que mudam dados estão em escrita.py.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import Orcamento, Reserva, Voo
from app.schemas import ExtratoResponse, PassagemOut

router = APIRouter(prefix="/orcamentos", tags=["Orçamentos (Queries)"])


@router.get(
    "/{roteiro_id}/extrato",
    response_model=ExtratoResponse,
    summary="Extrato do orçamento: saldo e passagens do roteiro",
)
def extrato(roteiro_id: int, session: Session = Depends(get_session)):
    resultado = consultar_extrato(session, roteiro_id)
    if resultado is None:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado para este roteiro.")
    return resultado


def consultar_extrato(session: Session, roteiro_id: int) -> Optional[ExtratoResponse]:
    """Devolve o extrato, ou None se o roteiro ainda não tem orçamento."""
    orcamento = session.exec(select(Orcamento).where(Orcamento.roteiro_id == roteiro_id)).first()
    if orcamento is None:
        return None

    linhas = session.exec(
        select(Reserva, Voo)
        .join(Voo, Voo.id == Reserva.voo_id)
        .where(Reserva.roteiro_id == roteiro_id)
        .order_by(Reserva.id)
    ).all()

    return ExtratoResponse(
        roteiro_id=roteiro_id,
        teto_financeiro=orcamento.teto_financeiro,
        valor_utilizado=orcamento.valor_utilizado,
        saldo=round(orcamento.teto_financeiro - orcamento.valor_utilizado, 2),
        passagens=[
            PassagemOut(
                reserva_id=reserva.id,
                origem=voo.origem,
                destino=voo.destino,
                data=reserva.data_viagem,
                valor=reserva.valor_cobrado,
                status=reserva.status,
            )
            for reserva, voo in linhas
        ],
    )
