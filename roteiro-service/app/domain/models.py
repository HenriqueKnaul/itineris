from typing import Optional, List
from datetime import date
from pydantic import model_validator
from sqlmodel import SQLModel, Field, Relationship

class RoteiroBase(SQLModel):
    titulo: str
    data_inicio: date
    data_fim: date
    orcamento_teto: float
    status: str = "RASCUNHO"  # RASCUNHO, RESERVADO, CONFIRMADO, CANCELADO

    @model_validator(mode="after")
    def data_fim_nao_pode_ser_antes_da_data_inicio(self):
        if self.data_fim < self.data_inicio:
            raise ValueError("data_fim não pode ser anterior à data_inicio")
        return self

class Roteiro(RoteiroBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    usuario_id: int

    # cascade delete-orphan: apaga os destinos junto com o roteiro
    destinos: List["Destino"] = Relationship(
        back_populates="roteiro",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

class DestinoBase(SQLModel):
    cidade: str
    pais: str
    data_chegada: date
    data_partida: date
    ordem: int

class Destino(DestinoBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    roteiro_id: int = Field(foreign_key="roteiro.id")

    roteiro: Optional[Roteiro] = Relationship(back_populates="destinos")