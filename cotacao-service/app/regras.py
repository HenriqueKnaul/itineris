import unicodedata
from dataclasses import dataclass
from datetime import date
from typing import Iterable

ORIGEM_PADRAO = "Brasil"

LIMITE_OCUPACAO_ALTA = 0.80
LIMITE_OCUPACAO_MEDIA = 0.50
ACRESCIMO_OCUPACAO_ALTA = 0.30
ACRESCIMO_OCUPACAO_MEDIA = 0.15
DIAS_ANTECEDENCIA_MINIMA = 7
ACRESCIMO_ULTIMA_HORA = 0.20


@dataclass(frozen=True)
class Trecho:

    origem: str
    destino: str
    data: date


def normalizar_nome(nome: str) -> str:
    decomposto = unicodedata.normalize("NFKD", nome.strip())
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return " ".join(sem_acento.casefold().split())


def montar_trechos(destinos) -> list[Trecho]:

    if not destinos:
        raise ValueError("O roteiro precisa ter ao menos um destino.")

    trechos = []
    origem = ORIGEM_PADRAO
    for destino in destinos:
        trechos.append(Trecho(origem, destino.cidade, destino.data_chegada))
        origem = destino.cidade

    ultimo = destinos[-1]
    trechos.append(Trecho(ultimo.cidade, ORIGEM_PADRAO, ultimo.data_partida))
    return trechos

def calcular_ocupacao(capacidade: int, vagas: int) -> float:
    if capacidade <= 0:
        return 1.0
    ocupacao = (capacidade - vagas) / capacidade
    return min(max(ocupacao, 0.0), 1.0)


def calcular_tarifa(preco_base: float, capacidade: int, vagas: int, data_viagem: date, hoje: date) -> float:
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

def somar_valores(valores: Iterable[float]) -> float:
    return round(sum(valores), 2)


def orcamento_suficiente(total: float, teto: float) -> bool:
    return round(total, 2) <= round(teto, 2)


def calcular_faltante(total: float, teto: float) -> float:
    return max(0.0, round(total - teto, 2))
