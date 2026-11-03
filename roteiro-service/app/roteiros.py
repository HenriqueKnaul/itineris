from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.cotacao_client import FalhaDeComunicacao, cancelar_passagens, reservar_passagens
from app.database import get_session
from app.models import Destino, DestinoBase, Roteiro, RoteiroBase

router = APIRouter(prefix="/roteiros", tags=["Roteiros"])


class RoteiroCreate(RoteiroBase):
    usuario_id: int
    destinos: List[DestinoBase] = []


def _buscar_ou_404(session: Session, roteiro_id: int) -> Roteiro:
    roteiro = session.get(Roteiro, roteiro_id)
    if not roteiro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roteiro não encontrado")
    return roteiro


@router.post("/", response_model=Roteiro, status_code=status.HTTP_201_CREATED)
def criar_roteiro(payload: RoteiroCreate, session: Session = Depends(get_session)):
    dados = payload.model_dump(exclude={"destinos"})
    destinos = [Destino(**d.model_dump()) for d in payload.destinos]

    roteiro = Roteiro(**dados, destinos=destinos)
    session.add(roteiro)
    session.commit()
    session.refresh(roteiro)
    return roteiro


@router.get("/", response_model=List[Roteiro])
def listar_roteiros(session: Session = Depends(get_session)):
    return session.exec(select(Roteiro)).all()


@router.get("/{roteiro_id}", response_model=Roteiro)
def obter_roteiro(roteiro_id: int, session: Session = Depends(get_session)):
    return _buscar_ou_404(session, roteiro_id)


@router.delete("/{roteiro_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_roteiro(roteiro_id: int, session: Session = Depends(get_session)):
    session.delete(_buscar_ou_404(session, roteiro_id))
    session.commit()


@router.post("/{roteiro_id}/reservar", tags=["Saga"])
async def reservar(roteiro_id: int, session: Session = Depends(get_session)):
    roteiro = _buscar_ou_404(session, roteiro_id)

    if roteiro.status == "RESERVADO":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Este roteiro já está reservado.")
    if not roteiro.destinos:
        raise HTTPException(422, detail="O roteiro não tem destinos para reservar.")

    destinos_em_ordem = sorted(roteiro.destinos, key=lambda d: d.ordem)
    try:
        resultado = await reservar_passagens(roteiro.id, roteiro.orcamento_teto, destinos_em_ordem)
    except FalhaDeComunicacao as erro:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro))

    if resultado.get("status") != "aprovado":
        raise HTTPException(422, detail=resultado)

    roteiro.status = "RESERVADO"
    session.add(roteiro)
    try:
        session.commit()
    except Exception as erro_local:
        session.rollback()
        try:
            await cancelar_passagens(roteiro.id)
        except FalhaDeComunicacao as erro_compensacao:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Falha ao salvar o roteiro {roteiro.id} e a compensação também falhou. "
                    f"É preciso reconciliar manualmente com o cotacao-service. "
                    f"Erro local: {erro_local}. Erro da compensação: {erro_compensacao}"
                ),
            ) from erro_compensacao
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Não foi possível salvar o roteiro; a reserva foi cancelada (compensação da Saga). Erro: {erro_local}",
        ) from erro_local

    session.refresh(roteiro)
    return {"roteiro_id": roteiro.id, "status_roteiro": roteiro.status, **resultado}


@router.post("/{roteiro_id}/cancelar-reserva", tags=["Saga"])
async def cancelar_reserva(roteiro_id: int, session: Session = Depends(get_session)):
    roteiro = _buscar_ou_404(session, roteiro_id)

    if roteiro.status != "RESERVADO":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Este roteiro não está reservado; não há o que cancelar.")

    try:
        total_cancelado = await cancelar_passagens(roteiro.id)
    except FalhaDeComunicacao as erro:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro))

    roteiro.status = "CANCELADO"
    session.add(roteiro)
    session.commit()
    session.refresh(roteiro)

    return {"roteiro_id": roteiro.id, "status_roteiro": roteiro.status, "reservas_canceladas": total_cancelado}
