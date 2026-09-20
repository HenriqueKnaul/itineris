from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.infrastructure.database import get_session
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
    
    # 1. Instancia o objeto Roteiro (Mestre)
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
    session.refresh(novo_roteiro) # Atualiza para obter o ID gerado pelo banco

    # 2. Instancia os Destinos vinculados ao Roteiro criado (Detalhes)
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