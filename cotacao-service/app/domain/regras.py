"""Regras de negócio do Cotação Service: funções puras, sem acesso a banco/HTTP."""
import unicodedata
from dataclasses import dataclass
from datetime import date
from typing import Iterable, Sequence

from app.domain.constantes import ORIGEM_PADRAO

# --- Parâmetros da tarifa dinâmica -------------------------------------------
LIMITE_OCUPACAO_ALTA = 0.80
LIMITE_OCUPACAO_MEDIA = 0.50
ACRESCIMO_OCUPACAO_ALTA = 0.30
ACRESCIMO_OCUPACAO_MEDIA = 0.15
DIAS_ANTECEDENCIA_MINIMA = 7
ACRESCIMO_ULTIMA_HORA = 0.20


@dataclass(frozen=True)
class DestinoRoteiro:
    """Destino de um roteiro, como o roteiro-service o descreve."""

    cidade: str
    data_chegada: date
    data_partida: date


@dataclass(frozen=True)
class Trecho:
    """Uma perna da viagem (origem -> destino) numa data."""

    origem: str
    destino: str
    data: date


@dataclass(frozen=True)
class TrechoCotado:
    """Trecho já com o valor calculado pela tarifa dinâmica."""

    origem: str
    destino: str
    data: date
    valor: float


# --- Apoio -------------------------------------------------------------------
def normalizar_nome(nome: str) -> str:
    """Normaliza nomes de cidade para comparação: sem acento, minúsculo, sem espaços extras."""
    decomposto = unicodedata.normalize("NFKD", nome.strip())
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return " ".join(sem_acento.casefold().split())


def montar_trechos(
    destinos: Sequence[DestinoRoteiro], base: str = ORIGEM_PADRAO
) -> list[Trecho]:
    """Monta os trechos do roteiro: ida, entre destinos e volta.

    Para D1..Dn: base->D1, D1->D2, ..., D(n-1)->Dn, Dn->base.
    Datas: cada ida/troca usa a data_chegada do destino de chegada;
    a volta usa a data_partida do último destino.
    """
    if not destinos:
        raise ValueError("O roteiro precisa ter ao menos um destino.")

    trechos: list[Trecho] = []
    origem = base
    for destino in destinos:
        trechos.append(Trecho(origem, destino.cidade, destino.data_chegada))
        origem = destino.cidade

    ultimo = destinos[-1]
    trechos.append(Trecho(ultimo.cidade, base, ultimo.data_partida))
    return trechos


# --- RN1: tarifa dinâmica ----------------------------------------------------
def calcular_ocupacao(capacidade: int, vagas: int) -> float:
    """Fração de assentos já ocupados, entre 0.0 e 1.0."""
    if capacidade <= 0:
        return 1.0
    ocupacao = (capacidade - vagas) / capacidade
    return min(max(ocupacao, 0.0), 1.0)


def calcular_tarifa(
    preco_base: float,
    capacidade: int,
    vagas: int,
    data_viagem: date,
    hoje: date,
) -> float:
    """Acréscimo por ocupação (>=80% +30%, >=50% +15%) somado ao de última hora (<7 dias: +20%)."""
    ocupacao = calcular_ocupacao(capacidade, vagas)
    if ocupacao >= LIMITE_OCUPACAO_ALTA:
        acrescimo = ACRESCIMO_OCUPACAO_ALTA
    elif ocupacao >= LIMITE_OCUPACAO_MEDIA:
        acrescimo = ACRESCIMO_OCUPACAO_MEDIA
    else:
        acrescimo = 0.0

    if (data_viagem - hoje).days < DIAS_ANTECEDENCIA_MINIMA:
        acrescimo += ACRESCIMO_ULTIMA_HORA

    return round(preco_base * (1 + acrescimo), 2)


# --- RN2: orçamento ----------------------------------------------------------
def somar_valores(valores: Iterable[float]) -> float:
    """Soma valores monetários evitando ruído de ponto flutuante."""
    return round(sum(valores), 2)


def orcamento_suficiente(total: float, teto: float) -> bool:
    """O total cabe no teto? (igual ao teto ainda é aprovado)."""
    return round(total, 2) <= round(teto, 2)


def calcular_faltante(total: float, teto: float) -> float:
    """Quanto falta para o teto cobrir o total (0 se já cobre)."""
    return max(0.0, round(total - teto, 2))
