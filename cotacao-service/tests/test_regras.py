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


def test_tarifa_ocupacao_alta_acrescenta_30_por_cento():
    assert calcular_tarifa(1000, 100, 20, LONGE, HOJE) == 1300.0


def test_tarifa_limites_de_ocupacao():
    assert calcular_tarifa(1000, 100, 51, LONGE, HOJE) == 1000.0  # 49% ocupado
    assert calcular_tarifa(1000, 100, 50, LONGE, HOJE) == 1150.0  # 50% ocupado
    assert calcular_tarifa(1000, 100, 21, LONGE, HOJE) == 1150.0  # 79% ocupado
    assert calcular_tarifa(1000, 100, 20, LONGE, HOJE) == 1300.0  # 80% ocupado


def test_tarifa_ultima_hora_acrescenta_20_por_cento():
    assert calcular_tarifa(1000, 100, 100, HOJE + timedelta(days=6), HOJE) == 1200.0


def test_tarifa_com_exatamente_7_dias_nao_tem_acrescimo():
    assert calcular_tarifa(1000, 100, 100, HOJE + timedelta(days=7), HOJE) == 1000.0


def test_tarifa_acrescimos_se_somam():
    # ocupação alta (+30%) e última hora (+20%) sobre o preço base
    assert calcular_tarifa(1000, 100, 10, HOJE + timedelta(days=2), HOJE) == 1500.0


def test_tarifa_arredonda_para_duas_casas():
    assert calcular_tarifa(333.33, 100, 50, LONGE, HOJE) == round(333.33 * 1.15, 2)


def test_ocupacao_de_voo_sem_capacidade_conta_como_lotado():
    assert calcular_ocupacao(0, 0) == 1.0


# ---------- Trechos do roteiro ----------
def test_roteiro_com_um_destino_tem_ida_e_volta():
    destinos = [DestinoRoteiro("Lisboa", date(2026, 12, 10), date(2026, 12, 15))]

    trechos = montar_trechos(destinos)

    assert [(t.origem, t.destino, t.data) for t in trechos] == [
        ("Brasil", "Lisboa", date(2026, 12, 10)),
        ("Lisboa", "Brasil", date(2026, 12, 15)),
    ]


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


def test_roteiro_sem_destinos_e_invalido():
    with pytest.raises(ValueError):
        montar_trechos([])


def test_normalizar_nome_ignora_acento_caixa_e_espacos():
    assert normalizar_nome("  TÓQUIO ") == "toquio"
    assert normalizar_nome("Buenos   Aires") == "buenos aires"


# ---------- RN2: orçamento ----------
def test_somar_valores_evita_ruido_de_ponto_flutuante():
    assert somar_valores([0.1, 0.2]) == 0.3


def test_orcamento_suficiente_quando_sobra_dinheiro():
    assert orcamento_suficiente(2500, 3000) is True


def test_orcamento_suficiente_quando_total_igual_ao_teto():
    assert orcamento_suficiente(2500, 2500) is True


def test_orcamento_insuficiente_quando_total_passa_do_teto():
    assert orcamento_suficiente(2500.01, 2500) is False


def test_faltante_e_a_diferenca_entre_total_e_teto():
    assert calcular_faltante(2500, 2000) == 500.0


def test_faltante_e_zero_quando_o_teto_cobre():
    assert calcular_faltante(2500, 3000) == 0.0
