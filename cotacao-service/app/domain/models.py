"""Entidades do domínio do Cotação Service (tabelas SQLModel)."""
from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint

from app.domain.constantes import ORIGEM_PADRAO



class StatusReserva(str, Enum):
    CONFIRMADA = "CONFIRMADA"
    CANCELADA = "CANCELADA"


def _agora() -> datetime:
    return datetime.now(timezone.utc)


class Voo(SQLModel, table=True):
    """Catálogo fictício de voos. Um registro por rota (origem -> destino)."""

    __table_args__ = (UniqueConstraint("origem", "destino"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    origem: str = Field(default=ORIGEM_PADRAO, index=True)
    destino: str = Field(index=True)
    preco_base: float
    capacidade: int  # total de assentos (usado para calcular a ocupação)
    vagas: int  # assentos ainda disponíveis (0 <= vagas <= capacidade)


class Orcamento(SQLModel, table=True):
    """Orçamento de um roteiro.

    O teto é informado pelo roteiro-service (que é o dono desse dado) e aqui
    fica apenas como registro do que foi usado na reserva.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    roteiro_id: int = Field(unique=True, index=True)  # sem FK: bancos isolados
    teto_financeiro: float
    valor_utilizado: float = 0.0


class Reserva(SQLModel, table=True):
    """Passagem comprada para um roteiro (necessária para extrato e cancelamento)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    roteiro_id: int = Field(index=True)
    voo_id: int = Field(foreign_key="voo.id")
    data_viagem: date
    valor_cobrado: float  # já com a tarifa dinâmica aplicada
    status: str = Field(default=StatusReserva.CONFIRMADA.value)
    criada_em: datetime = Field(default_factory=_agora)
