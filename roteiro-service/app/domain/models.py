from typing import Optional, List
from datetime import date
from sqlmodel import SQLModel, Field, Relationship

class RoteiroBase(SQLModel):
    titulo: str
    data_inicio: date
    data_fim: date
    orcamento_teto: float
    status: str = "RASCUNHO"  # RASCUNHO, RESERVADO, CONFIRMADO, CANCELADO

class Roteiro(RoteiroBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    usuario_id: int

    # Relacionamento Mestre-Detalhe (1 Roteiro tem muitos Destinos)
    destinos: List["Destino"] = Relationship(back_populates="roteiro")

class DestinoBase(SQLModel):
    cidade: str
    pais: str
    data_chegada: date
    data_partida: date
    ordem: int

class Destino(DestinoBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    roteiro_id: int = Field(foreign_key="roteiro.id")

    # Referência de volta para o Roteiro pai
    roteiro: Optional[Roteiro] = Relationship(back_populates="destinos")