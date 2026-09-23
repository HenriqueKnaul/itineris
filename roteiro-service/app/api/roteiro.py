from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.infrastructure.database import get_session
from app.infrastructure.cotacao_client import (
    FalhaDeComunicacao,
    ReservaRejeitada,
    cancelar_passagens,
    reservar_passagens,
)
from app.domain.models import Roteiro, Destino, RoteiroBase, DestinoBase

router = APIRouter(prefix="/roteiros", tags=["Roteiros"])

# Modelos de transferência de dados (DTOs) para envio e resposta
class DestinoCreate(DestinoBase):
    pass

class RoteiroCreate(RoteiroBase):
    usuario_id: int
    destinos: List[DestinoCreate] = []

@router.post("/", response_model=Roteiro, status_code=status.HTTP_201_CREATED)
def criar_roteiro(payload: RoteiroCreate, session: Session = Depends(get_session)):
    """Cria um novo roteiro de viagem junto com a sua lista de destinos."""
    novo_roteiro = Roteiro(
        titulo=payload.titulo,
        data_inicio=payload.data_inicio,
        data_fim=payload.data_fim,
        orcamento_teto=payload.orcamento_teto,
        status=payload.status,
        usuario_id=payload.usuario_id
    )
    
    session.add(novo_roteiro)
    session.commit()
    session.refresh(novo_roteiro)  # pega o ID gerado pelo banco

    for dest in payload.destinos:
        novo_destino = Destino(
            cidade=dest.cidade,
            pais=dest.pais,
            data_chegada=dest.data_chegada,
            data_partida=dest.data_partida,
            ordem=dest.ordem,
            roteiro_id=novo_roteiro.id
        )
        session.add(novo_destino)
    
    session.commit()
    session.refresh(novo_roteiro)
    return novo_roteiro


@router.get("/", response_model=List[Roteiro])
def listar_roteiros(session: Session = Depends(get_session)):
    """Retorna todos os roteiros cadastrados no sistema."""
    statement = select(Roteiro)
    resultados = session.exec(statement).all()
    return resultados


@router.get("/{roteiro_id}", response_model=Roteiro)
def obter_roteiro(roteiro_id: int, session: Session = Depends(get_session)):
    """Busca um roteiro específico pelo ID."""
    roteiro = session.get(Roteiro, roteiro_id)
    if not roteiro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Roteiro não encontrado"
        )
    return roteiro


@router.delete("/{roteiro_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_roteiro(roteiro_id: int, session: Session = Depends(get_session)):
    """Remove um roteiro e seus destinos do banco de dados."""
    roteiro = session.get(Roteiro, roteiro_id)
    if not roteiro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Roteiro não encontrado"
        )
    session.delete(roteiro)
    session.commit()
    return None


# --- Saga de reserva (orquestrada pelo roteiro-service) ---------------------
@router.post("/{roteiro_id}/reservar", tags=["Roteiros", "Saga"])
async def reservar(roteiro_id: int, session: Session = Depends(get_session)):
    """Aciona a reserva das passagens do roteiro junto ao cotacao-service."""
    roteiro = session.get(Roteiro, roteiro_id)
    if not roteiro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roteiro não encontrado")

    if roteiro.status == "RESERVADO":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este roteiro já está reservado.",
        )
    if not roteiro.destinos:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O roteiro não tem destinos para reservar.",
        )

    destinos_payload = [
        {
            "cidade": destino.cidade,
            "data_chegada": destino.data_chegada,
            "data_partida": destino.data_partida,
        }
        for destino in sorted(roteiro.destinos, key=lambda d: d.ordem)
    ]

    try:
        resultado = await reservar_passagens(
            roteiro_id=roteiro.id,
            teto_financeiro=roteiro.orcamento_teto,
            destinos=destinos_payload,
        )
    except FalhaDeComunicacao as erro:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro))

    if isinstance(resultado, ReservaRejeitada):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=resultado.model_dump(),
        )

    # se o commit local falhar, precisa desfazer a reserva já feita no cotacao-service
    roteiro.status = "RESERVADO"
    session.add(roteiro)
    try:
        session.commit()
    except Exception as erro_local:
        session.rollback()
        try:
            await cancelar_passagens(roteiro.id)
        except FalhaDeComunicacao as erro_compensacao:
            # nem o commit local nem a compensação deram certo: precisa reconciliar na mão
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Falha ao confirmar o roteiro após a reserva ter sido aprovada, e a "
                    "compensação automática também falhou. É necessário reconciliar "
                    f"manualmente o roteiro {roteiro.id} no cotacao-service. "
                    f"Erro local: {erro_local}. Erro da compensação: {erro_compensacao}"
                ),
            ) from erro_compensacao
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Não foi possível confirmar o roteiro após a reserva aprovada; a reserva "
                f"foi automaticamente cancelada (compensação da Saga). Erro original: {erro_local}"
            ),
        ) from erro_local

    session.refresh(roteiro)

    return {
        "roteiro_id": roteiro.id,
        "status_roteiro": roteiro.status,
        **resultado.model_dump(),
    }


@router.post("/{roteiro_id}/cancelar-reserva", tags=["Roteiros", "Saga"])
async def cancelar_reserva(roteiro_id: int, session: Session = Depends(get_session)):
    """Compensação da Saga: desfaz a reserva de um roteiro já RESERVADO."""
    roteiro = session.get(Roteiro, roteiro_id)
    if not roteiro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roteiro não encontrado")

    if roteiro.status != "RESERVADO":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este roteiro não está reservado; não há o que cancelar.",
        )

    try:
        total_cancelado = await cancelar_passagens(roteiro.id)
    except FalhaDeComunicacao as erro:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro))

    roteiro.status = "CANCELADO"
    session.add(roteiro)
    session.commit()
    session.refresh(roteiro)

    return {
        "roteiro_id": roteiro.id,
        "status_roteiro": roteiro.status,
        "reservas_canceladas": total_cancelado,
    }