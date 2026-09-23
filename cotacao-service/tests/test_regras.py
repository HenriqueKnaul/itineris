"""Testes das regras de negócio puras (sem banco e sem HTTP)."""
from datetime import date, timedelta

import pytest

from app.domain.regras import (
    DestinoRoteiro,
    calcular_faltante,
    calcular_ocupacao,
    calcular_tarifa,
    montar_trechos,
    normalizar_nome,
    orcamento_suficiente,
    somar_valores,
)

HOJE = date(2026, 1, 1)
LONGE = HOJE + timedelta(days=60)


# ---------- RN1: tarifa dinâmica ----------
def test_tarifa_sem_acrescimo_com_voo_vazio_e_data_distante():
    assert calcular_tarifa(1000, 100, 100, LONGE, HOJE) == 1000.0


def test_tarifa_ocupacao_media_acrescenta_15_por_cento():
    assert calcular_tarifa(1000, 100, 50, LONGE, HOJE) == 1150.0


def test_roteiro_com_dois_destinos_tem_tres_trechos():
    destinos = [
        DestinoRoteiro("Lisboa", date(2026, 12, 10), date(2026, 12, 15)),
        DestinoRoteiro("Paris", date(2026, 12, 15), date(2026, 12, 20)),
    ]

    trechos = montar_trechos(destinos)

    assert [(t.origem, t.destino, t.data) for t in trechos] == [
        ("Brasil", "Lisboa", date(2026, 12, 10)),
        ("Lisboa", "Paris", date(2026, 12, 15)),
        ("Paris", "Brasil", date(2026, 12, 20)),
    ]


def test_normalizar_nome_ignora_acento_caixa_e_espacos():
    assert normalizar_nome("  TÓQUIO ") == "toquio"
    assert normalizar_nome("Buenos   Aires") == "buenos aires"


# ---------- RN2: orçamento ----------
def test_orcamento_suficiente_quando_sobra_dinheiro():
    assert orcamento_suficiente(2500, 3000) is True


def test_faltante_e_a_diferenca_entre_total_e_teto():
    assert calcular_faltante(2500, 2000) == 500.0


