from collections import Counter
from datetime import date
from typing import Optional, Union

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import CANCELADA, CONFIRMADA, Orcamento, Reserva, Voo
from app.regras import (
    calcular_faltante,
    calcular_tarifa,
    montar_trechos,
    normalizar_nome,
    orcamento_suficiente,
    somar_valores,
)
from app.schemas import (
    CancelarRequest,
    CancelarResponse,
    ReservaAprovada,
    ReservaItem,
    ReservaRejeitada,
    ReservarRequest,
    TrechoOut,
)

router = APIRouter(prefix="/cotacoes", tags=["Cotações (Commands)"])


class Rejeicao(Exception):

    def __init__(self, motivo: str, mensagem: str, **detalhes):
        super().__init__(mensagem)
        self.motivo = motivo
        self.mensagem = mensagem
        self.detalhes = detalhes


@router.post(
    "/reservar",
    response_model=Union[ReservaAprovada, ReservaRejeitada],
    response_model_exclude_none=True,
    summary="Reserva todas as passagens do roteiro (tudo ou nada)",
)
def reservar(pedido: ReservarRequest, session: Session = Depends(get_session)):
    try:
        return reservar_roteiro(session, pedido)
    except Rejeicao as erro:
        return ReservaRejeitada(motivo=erro.motivo, mensagem=erro.mensagem, **erro.detalhes)


@router.post("/cancelar", response_model=CancelarResponse, summary="Cancela as reservas do roteiro (compensação da Saga)")
def cancelar(pedido: CancelarRequest, session: Session = Depends(get_session)):
    return CancelarResponse(reservas_canceladas=cancelar_reservas(session, pedido.roteiro_id))


def reservar_roteiro(session: Session, pedido: ReservarRequest, hoje: Optional[date] = None) -> ReservaAprovada:
    hoje = hoje or date.today()

    ja_reservadas = _reservas_confirmadas(session, pedido.roteiro_id)
    if ja_reservadas:
        return _aprovacao_ja_existente(session, pedido.roteiro_id, ja_reservadas)

    trechos = montar_trechos(pedido.destinos)
    catalogo = {
        (normalizar_nome(v.origem), normalizar_nome(v.destino)): v for v in session.exec(select(Voo)).all()
    }

    voos = []
    for trecho in trechos:
        voo = catalogo.get((normalizar_nome(trecho.origem), normalizar_nome(trecho.destino)))
        if voo is None:
            raise Rejeicao(
                "voo_nao_encontrado",
                f"Não há voo cadastrado para o trecho {trecho.origem} → {trecho.destino}.",
                trecho=TrechoOut(origem=trecho.origem, destino=trecho.destino, data=trecho.data),
            )
        voos.append(voo)

    vagas_necessarias = Counter(voo.id for voo in voos)
    for trecho, voo in zip(trechos, voos):
        if voo.vagas < vagas_necessarias[voo.id]:
            raise Rejeicao(
                "sem_vagas",
                f"Não há vagas para o trecho {trecho.origem} → {trecho.destino}.",
                trecho=TrechoOut(origem=trecho.origem, destino=trecho.destino, data=trecho.data),
            )

    valores = [
        calcular_tarifa(voo.preco_base, voo.capacidade, voo.vagas, trecho.data, hoje)
        for trecho, voo in zip(trechos, voos)
    ]
    total = somar_valores(valores)
    if not orcamento_suficiente(total, pedido.teto_financeiro):
        raise Rejeicao(
            "sem_saldo",
            "O orçamento não é suficiente para as passagens deste roteiro.",
            teto_financeiro=pedido.teto_financeiro,
            valor_minimo_necessario=total,
            valor_faltante=calcular_faltante(total, pedido.teto_financeiro),
            trechos=[
                TrechoOut(origem=voo.origem, destino=voo.destino, data=trecho.data, valor=valor)
                for trecho, voo, valor in zip(trechos, voos, valores)
            ],
        )

    try:
        voos_por_id = {voo.id: voo for voo in voos}
        for voo_id, quantidade in vagas_necessarias.items():
            voos_por_id[voo_id].vagas -= quantidade
            session.add(voos_por_id[voo_id])

        orcamento = _buscar_orcamento(session, pedido.roteiro_id) or Orcamento(
            roteiro_id=pedido.roteiro_id, teto_financeiro=pedido.teto_financeiro
        )
        orcamento.teto_financeiro = pedido.teto_financeiro
        orcamento.valor_utilizado = total
        session.add(orcamento)

        reservas = [
            Reserva(roteiro_id=pedido.roteiro_id, voo_id=voo.id, data_viagem=trecho.data, valor_cobrado=valor)
            for trecho, voo, valor in zip(trechos, voos, valores)
        ]
        session.add_all(reservas)
        session.commit()
    except Exception:
        session.rollback()
        raise

    return ReservaAprovada(
        valor_total=total,
        saldo_restante=round(pedido.teto_financeiro - total, 2),
        reservas=[
            ReservaItem(reserva_id=r.id, origem=voo.origem, destino=voo.destino, data=trecho.data, valor=valor)
            for r, trecho, voo, valor in zip(reservas, trechos, voos, valores)
        ],
    )


def cancelar_reservas(session: Session, roteiro_id: int) -> int:
    reservas = _reservas_confirmadas(session, roteiro_id)
    if not reservas:
        return 0

    try:
        valor_devolvido = 0.0
        for reserva in reservas:
            voo = session.get(Voo, reserva.voo_id)
            voo.vagas = min(voo.vagas + 1, voo.capacidade)
            session.add(voo)

            reserva.status = CANCELADA
            session.add(reserva)
            valor_devolvido += reserva.valor_cobrado

        orcamento = _buscar_orcamento(session, roteiro_id)
        if orcamento is not None:
            orcamento.valor_utilizado = max(0.0, round(orcamento.valor_utilizado - valor_devolvido, 2))
            session.add(orcamento)

        session.commit()
    except Exception:
        session.rollback()
        raise

    return len(reservas)


def _buscar_orcamento(session: Session, roteiro_id: int) -> Optional[Orcamento]:
    return session.exec(select(Orcamento).where(Orcamento.roteiro_id == roteiro_id)).first()


def _reservas_confirmadas(session: Session, roteiro_id: int) -> list[Reserva]:
    consulta = (
        select(Reserva)
        .where(Reserva.roteiro_id == roteiro_id, Reserva.status == CONFIRMADA)
        .order_by(Reserva.id)
    )
    return list(session.exec(consulta).all())


def _aprovacao_ja_existente(session: Session, roteiro_id: int, reservas: list[Reserva]) -> ReservaAprovada:
    itens = []
    for reserva in reservas:
        voo = session.get(Voo, reserva.voo_id)
        itens.append(
            ReservaItem(
                reserva_id=reserva.id,
                origem=voo.origem,
                destino=voo.destino,
                data=reserva.data_viagem,
                valor=reserva.valor_cobrado,
            )
        )
    total = somar_valores(item.valor for item in itens)
    orcamento = _buscar_orcamento(session, roteiro_id)
    teto = orcamento.teto_financeiro if orcamento else total
    return ReservaAprovada(valor_total=total, saldo_restante=round(teto - total, 2), reservas=itens)