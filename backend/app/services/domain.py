"""Estruturas de domínio puras usadas pelas funções de cálculo.

Estas dataclasses são desacopladas do SQLAlchemy e do FastAPI para que os
módulos ``services.metrics`` e ``services.tax`` possam ser testados com pytest
sem banco de dados. A camada de persistência converte os modelos ORM nestas
estruturas (ver ``app.services.adapters``).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.enums import CategoriaDespesa


@dataclass(frozen=True)
class ApartamentoData:
    """Apartamento considerado nos cálculos."""

    id: int
    nome: str
    data_inicio_operacao: date
    ativo: bool = True


@dataclass(frozen=True)
class ReservaData:
    """Reserva. Valores monetários sempre em :class:`~decimal.Decimal`."""

    apartamento_id: int
    check_in: date
    check_out: date
    num_hospedes: int
    valor_hospedagem: Decimal
    taxa_limpeza: Decimal = Decimal("0")
    comissao: Decimal = Decimal("0")
    cancelada: bool = False

    @property
    def noites_totais(self) -> int:
        """Número de noites contratadas (a noite do check-out não conta)."""
        return (self.check_out - self.check_in).days

    @property
    def receita_liquida_total(self) -> Decimal:
        """``valor_hospedagem + taxa_limpeza - comissao`` (reserva inteira)."""
        return self.valor_hospedagem + self.taxa_limpeza - self.comissao


@dataclass(frozen=True)
class DespesaData:
    """Despesa. ``apartamento_id is None`` => despesa comum (rateada/geral)."""

    data: date
    categoria: CategoriaDespesa
    valor: Decimal
    dedutivel_ir: bool = False
    apartamento_id: int | None = None


@dataclass(frozen=True)
class FaixaIR:
    """Faixa da tabela progressiva mensal do Carnê-Leão."""

    limite_inferior: Decimal
    aliquota: Decimal  # fração: 0.075 = 7,5%
    parcela_deduzir: Decimal


@dataclass(frozen=True)
class ParametrosIR:
    """Parâmetros tributários versionados por ano (vêm do banco)."""

    ano_vigencia: int
    faixas: list[FaixaIR]
    isencao_efetiva: Decimal
    transicao_inicio: Decimal
    transicao_fim: Decimal
    # Quando False (default e valor seedado), a faixa de transição não reduz o
    # imposto: vale o "penhasco" (isento até a isenção, imposto cheio acima).
    # Isto reproduz a planilha validada (ver app/seed_data.py e os testes).
    # Quando True, aplica-se a interpolação linear do redutor de transição.
    aplicar_redutor_transicao: bool = False
