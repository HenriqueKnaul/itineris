"""Tabelas do banco do cotacao-service."""
from datetime import date, datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint

CONFIRMADA = "CONFIRMADA"
CANCELADA = "CANCELADA"


class Voo(SQLModel, table=True):
    """Catálogo fictício de voos: um registro por rota (origem -> destino)."""

    __table_args__ = (UniqueConstraint("origem", "destino"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    origem: str = Field(index=True)
    destino: str = Field(index=True)
    preco_base: float
    capacidade: int  # total de assentos
    vagas: int  # assentos ainda livres


class Orcamento(SQLModel, table=True):
    """Quanto o roteiro pode gastar (teto) e quanto já gastou em passagens."""

    id: Optional[int] = Field(default=None, primary_key=True)
    roteiro_id: int = Field(unique=True, index=True)  # sem FK: cada serviço tem o seu banco
    teto_financeiro: float
    valor_utilizado: float = 0.0


class Reserva(SQLModel, table=True):
    """Uma passagem comprada para um roteiro."""

    id: Optional[int] = Field(default=None, primary_key=True)
    roteiro_id: int = Field(index=True)
    voo_id: int = Field(foreign_key="voo.id")
    data_viagem: date
    valor_cobrado: float  # já com a tarifa dinâmica
    status: str = Field(default=CONFIRMADA)
    criada_em: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
