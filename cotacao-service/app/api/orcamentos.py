"""Rotas de CONSULTA (leitura) do Cotação Service."""
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api.schemas import ExtratoResponse
from app.application.queries.consultar_extrato import consultar_extrato
from app.infrastructure.database import get_session

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
    return asdict(resultado)
