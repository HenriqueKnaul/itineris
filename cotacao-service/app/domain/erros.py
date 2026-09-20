"""Rejeições de negócio do Cotação Service.

São situações esperadas (não são bugs): a camada de API as converte em
`{"status": "rejeitado", "motivo": ...}` com HTTP 200, conforme o contrato
combinado com o roteiro-service.
"""
from typing import Sequence

from app.domain.regras import Trecho, TrechoCotado, calcular_faltante


class ErroDeNegocio(Exception):
    motivo = "erro_de_negocio"

    def __init__(self, mensagem: str):
        super().__init__(mensagem)
        self.mensagem = mensagem


class VooNaoEncontrado(ErroDeNegocio):
    motivo = "voo_nao_encontrado"

    def __init__(self, trecho: Trecho):
        super().__init__(
            f"Não há voo cadastrado para o trecho {trecho.origem} → {trecho.destino}."
        )
        self.trecho = trecho


class SemVagas(ErroDeNegocio):
    motivo = "sem_vagas"

    def __init__(self, trecho: Trecho):
        super().__init__(f"Não há vagas para o trecho {trecho.origem} → {trecho.destino}.")
        self.trecho = trecho


class SemSaldo(ErroDeNegocio):
    motivo = "sem_saldo"

    def __init__(
        self,
        teto_financeiro: float,
        valor_minimo_necessario: float,
        trechos: Sequence[TrechoCotado],
    ):
        super().__init__("O orçamento não é suficiente para as passagens deste roteiro.")
        self.teto_financeiro = teto_financeiro
        self.valor_minimo_necessario = valor_minimo_necessario
        self.valor_faltante = calcular_faltante(valor_minimo_necessario, teto_financeiro)
        self.trechos = list(trechos)
