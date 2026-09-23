"""Comando: reservar todas as passagens de um roteiro (tudo ou nada).

Não conhece FastAPI: recebe um comando, aplica as regras do domínio, grava no
banco e devolve um resultado. Rejeições de negócio saem como exceções de
`app.domain.erros`.
"""
from collections import Counter
from dataclasses import dataclass
from datetime import date
from typing import Optional, Sequence

from sqlmodel import Session

from app.domain.erros import SemSaldo, SemVagas, VooNaoEncontrado
from app.domain.models import Orcamento, Reserva
from app.domain.regras import (
    DestinoRoteiro,
    TrechoCotado,
    calcular_tarifa,
    montar_trechos,
    normalizar_nome,
    orcamento_suficiente,
    somar_valores,
)
from app.infrastructure.write_model import repositorio


@dataclass(frozen=True)
class ReservarRoteiroCommand:
    roteiro_id: int
    teto_financeiro: float
    destinos: Sequence[DestinoRoteiro]


@dataclass(frozen=True)
class ReservaConfirmada:
    reserva_id: int
    origem: str
    destino: str
    data: date
    valor: float


@dataclass(frozen=True)
class ResultadoReserva:
    reservas: list[ReservaConfirmada]
    valor_total: float
    saldo_restante: float


def reservar_roteiro(
    session: Session,
    comando: ReservarRoteiroCommand,
    hoje: Optional[date] = None,
) -> ResultadoReserva:
    hoje = hoje or date.today()

    # idempotência: a Saga pode repetir a chamada
    ja_reservadas = repositorio.listar_reservas_confirmadas(session, comando.roteiro_id)
    if ja_reservadas:
        return _resultado_ja_existente(session, comando.roteiro_id, ja_reservadas)

    trechos = montar_trechos(comando.destinos)
    catalogo = {
        (normalizar_nome(v.origem), normalizar_nome(v.destino)): v
        for v in repositorio.listar_voos(session)
    }

    voos = []
    for trecho in trechos:
        voo = catalogo.get((normalizar_nome(trecho.origem), normalizar_nome(trecho.destino)))
        if voo is None:
            raise VooNaoEncontrado(trecho)
        voos.append(voo)

    # mesmo voo pode aparecer em mais de um trecho
    demanda = Counter(voo.id for voo in voos)
    for trecho, voo in zip(trechos, voos):
        if voo.vagas < demanda[voo.id]:
            raise SemVagas(trecho)

    cotados = [
        TrechoCotado(
            origem=voo.origem,
            destino=voo.destino,
            data=trecho.data,
            valor=calcular_tarifa(voo.preco_base, voo.capacidade, voo.vagas, trecho.data, hoje),
        )
        for trecho, voo in zip(trechos, voos)
    ]
    total = somar_valores(c.valor for c in cotados)

    if not orcamento_suficiente(total, comando.teto_financeiro):
        raise SemSaldo(comando.teto_financeiro, total, cotados)

    try:
        for voo_id, quantidade in demanda.items():
            voo = next(v for v in voos if v.id == voo_id)
            voo.vagas -= quantidade
            session.add(voo)

        orcamento = repositorio.buscar_orcamento(session, comando.roteiro_id)
        if orcamento is None:
            orcamento = Orcamento(
                roteiro_id=comando.roteiro_id,
                teto_financeiro=comando.teto_financeiro,
                valor_utilizado=total,
            )
        else:  # reserva refeita depois de um cancelamento
            orcamento.teto_financeiro = comando.teto_financeiro
            orcamento.valor_utilizado = total
        session.add(orcamento)

        reservas = [
            Reserva(
                roteiro_id=comando.roteiro_id,
                voo_id=voo.id,
                data_viagem=cotado.data,
                valor_cobrado=cotado.valor,
            )
            for voo, cotado in zip(voos, cotados)
        ]
        session.add_all(reservas)
        session.commit()
    except Exception:
        session.rollback()
        raise

    return ResultadoReserva(
        reservas=[
            ReservaConfirmada(
                reserva_id=reserva.id,
                origem=cotado.origem,
                destino=cotado.destino,
                data=cotado.data,
                valor=cotado.valor,
            )
            for reserva, cotado in zip(reservas, cotados)
        ],
        valor_total=total,
        saldo_restante=round(comando.teto_financeiro - total, 2),
    )


def _resultado_ja_existente(
    session: Session, roteiro_id: int, reservas: list[Reserva]
) -> ResultadoReserva:
    confirmadas = []
    for reserva in reservas:
        voo = repositorio.buscar_voo(session, reserva.voo_id)
        confirmadas.append(
            ReservaConfirmada(
                reserva_id=reserva.id,
                origem=voo.origem,
                destino=voo.destino,
                data=reserva.data_viagem,
                valor=reserva.valor_cobrado,
            )
        )
    total = somar_valores(r.valor for r in confirmadas)
    orcamento = repositorio.buscar_orcamento(session, roteiro_id)
    teto = orcamento.teto_financeiro if orcamento else total
    return ResultadoReserva(
        reservas=confirmadas,
        valor_total=total,
        saldo_restante=round(teto - total, 2),
    )
