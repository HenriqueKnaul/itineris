"""Contratos HTTP (entrada e saída) do Cotação Service."""
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------- Entrada ----------
class DestinoIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    cidade: str = Field(min_length=1)
    data_chegada: date
    data_partida: date

    @model_validator(mode="after")
    def partida_nao_pode_ser_antes_da_chegada(self):
        if self.data_partida < self.data_chegada:
            raise ValueError("data_partida não pode ser anterior à data_chegada")
        return self


class ReservarRequest(BaseModel):
    roteiro_id: int
    teto_financeiro: float = Field(ge=0)
    destinos: list[DestinoIn] = Field(min_length=1)


class CancelarRequest(BaseModel):
    roteiro_id: int


# ---------- Saída: reservar ----------
class ReservaItem(BaseModel):
    reserva_id: int
    origem: str
    destino: str
    data: date
    valor: float


class ReservaAprovada(BaseModel):
    status: Literal["aprovado"] = "aprovado"
    valor_total: float
    saldo_restante: float
    reservas: list[ReservaItem]


class TrechoOut(BaseModel):
    origem: str
    destino: str
    data: date
    valor: Optional[float] = None  # só presente quando o trecho foi cotado


class ReservaRejeitada(BaseModel):
    status: Literal["rejeitado"] = "rejeitado"
    motivo: str  # sem_saldo | sem_vagas | voo_nao_encontrado
    mensagem: str
    # preenchidos apenas em "sem_saldo"
    teto_financeiro: Optional[float] = None
    valor_minimo_necessario: Optional[float] = None
    valor_faltante: Optional[float] = None
    trechos: Optional[list[TrechoOut]] = None
    # preenchido em "sem_vagas" e "voo_nao_encontrado"
    trecho: Optional[TrechoOut] = None


# ---------- Saída: cancelar ----------
class CancelarResponse(BaseModel):
    status: Literal["cancelado"] = "cancelado"
    reservas_canceladas: int


# ---------- Saída: extrato ----------
class PassagemOut(BaseModel):
    reserva_id: int
    origem: str
    destino: str
    data: date
    valor: float
    status: str


class ExtratoResponse(BaseModel):
    roteiro_id: int
    teto_financeiro: float
    valor_utilizado: float
    saldo: float
    passagens: list[PassagemOut]
