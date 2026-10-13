from datetime import date, timedelta
from app.regras import calcular_tarifa, montar_trechos, orcamento_suficiente
from app.schemas import DestinoIn

HOJE = date(2026, 1, 1)
LONGE = HOJE + timedelta(days=60)


def test_tarifa_ocupacao_alta_acrescenta_30_por_cento():
    assert calcular_tarifa(1000, 100, 20, LONGE, HOJE) == 1300.0


def test_tarifa_de_ultima_hora_acrescenta_20_por_cento():
    assert calcular_tarifa(1000, 100, 100, HOJE + timedelta(days=3), HOJE) == 1200.0


def test_roteiro_com_dois_destinos_tem_tres_trechos():
    destinos = [
        DestinoIn(cidade="Lisboa", data_chegada=date(2026, 12, 10), data_partida=date(2026, 12, 15)),
        DestinoIn(cidade="Paris", data_chegada=date(2026, 12, 15), data_partida=date(2026, 12, 20)),
    ]
    trechos = montar_trechos(destinos)

    assert len(trechos) == 3
    assert trechos[0].origem == "Brasil"
    assert trechos[-1].destino == "Brasil"


def test_orcamento_suficiente():
    assert orcamento_suficiente(2500, 3000) is True
    assert orcamento_suficiente(3500, 3000) is False