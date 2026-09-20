"""Rotas de COMANDO (escrita) do Cotação Service.

A camada de API só traduz HTTP <-> comandos: nenhuma regra de negócio aqui.
"""
from typing import Union

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.schemas import (
    CancelarRequest,
    CancelarResponse,
    ReservaAprovada,
    ReservarRequest,
    ReservaItem,
    ReservaRejeitada,
    TrechoOut,
)
from app.application.commands.cancelar_reservas import cancelar_reservas
from app.application.commands.reservar_roteiro import (
    ReservarRoteiroCommand,
    reservar_roteiro,
)
from app.domain.erros import ErroDeNegocio, SemSaldo, SemVagas, VooNaoEncontrado
from app.domain.regras import DestinoRoteiro
from app.infrastructure.database import get_session

router = APIRouter(prefix="/cotacoes", tags=["Cotações (Commands)"])


@router.post(
    "/reservar",
    response_model=Union[ReservaAprovada, ReservaRejeitada],
    response_model_exclude_none=True,
    summary="Reserva todas as passagens do roteiro (tudo ou nada)",
)
def reservar(payload: ReservarRequest, session: Session = Depends(get_session)):
    """Chamada pela Saga do roteiro-service.

    Rejeições de negócio (`sem_saldo`, `sem_vagas`, `voo_nao_encontrado`)
    retornam HTTP 200 com `status: "rejeitado"` no corpo.
    """
    comando = ReservarRoteiroCommand(
        roteiro_id=payload.roteiro_id,
        teto_financeiro=payload.teto_financeiro,
        destinos=[
            DestinoRoteiro(d.cidade, d.data_chegada, d.data_partida)
            for d in payload.destinos
        ],
    )
    try:
        resultado = reservar_roteiro(session, comando)
    except ErroDeNegocio as erro:
        return _rejeicao(erro)

    return ReservaAprovada(
        valor_total=resultado.valor_total,
        saldo_restante=resultado.saldo_restante,
        reservas=[
            ReservaItem(
                reserva_id=r.reserva_id,
                origem=r.origem,
                destino=r.destino,
                data=r.data,
                valor=r.valor,
            )
            for r in resultado.reservas
        ],
    )


@router.post(
    "/cancelar",
    response_model=CancelarResponse,
    summary="Cancela as reservas do roteiro (compensação da Saga)",
)
def cancelar(payload: CancelarRequest, session: Session = Depends(get_session)):
    total = cancelar_reservas(session, payload.roteiro_id)
    return CancelarResponse(reservas_canceladas=total)


def _rejeicao(erro: ErroDeNegocio) -> ReservaRejeitada:
    if isinstance(erro, SemSaldo):
        return ReservaRejeitada(
            motivo=erro.motivo,
            mensagem=erro.mensagem,
            teto_financeiro=erro.teto_financeiro,
            valor_minimo_necessario=erro.valor_minimo_necessario,
            valor_faltante=erro.valor_faltante,
            trechos=[
                TrechoOut(origem=t.origem, destino=t.destino, data=t.data, valor=t.valor)
                for t in erro.trechos
            ],
        )
    if isinstance(erro, (SemVagas, VooNaoEncontrado)):
        return ReservaRejeitada(
            motivo=erro.motivo,
            mensagem=erro.mensagem,
            trecho=TrechoOut(
                origem=erro.trecho.origem,
                destino=erro.trecho.destino,
                data=erro.trecho.data,
            ),
        )
    return ReservaRejeitada(motivo=erro.motivo, mensagem=erro.mensagem)
