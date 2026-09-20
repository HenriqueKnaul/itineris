"""Query: extrato do orçamento de um roteiro (lado de LEITURA do CQRS)."""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlmodel import Session

from app.infrastructure.read_model import extrato_repositorio


@dataclass(frozen=True)
class PassagemExtrato:
    reserva_id: int
    origem: str
    destino: str
    data: date
    valor: float
    status: str


@dataclass(frozen=True)
class ExtratoOrcamento:
    roteiro_id: int
    teto_financeiro: float
    valor_utilizado: float
    saldo: float
    passagens: list[PassagemExtrato]


def consultar_extrato(session: Session, roteiro_id: int) -> Optional[ExtratoOrcamento]:
    """Retorna o extrato, ou None se o roteiro ainda não tem orçamento."""
    orcamento = extrato_repositorio.buscar_orcamento(session, roteiro_id)
    if orcamento is None:
        return None

    passagens = [
        PassagemExtrato(
            reserva_id=reserva.id,
            origem=voo.origem,
            destino=voo.destino,
            data=reserva.data_viagem,
            valor=reserva.valor_cobrado,
            status=reserva.status,
        )
        for reserva, voo in extrato_repositorio.listar_passagens(session, roteiro_id)
    ]
    return ExtratoOrcamento(
        roteiro_id=roteiro_id,
        teto_financeiro=orcamento.teto_financeiro,
        valor_utilizado=orcamento.valor_utilizado,
        saldo=round(orcamento.teto_financeiro - orcamento.valor_utilizado, 2),
        passagens=passagens,
    )
