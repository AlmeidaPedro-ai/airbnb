"""Estimativa de Imposto de Renda — Carnê-Leão (funções puras).

Toda parametrização vem de ``ParametrosIR`` (banco), nunca de constantes no
código: a legislação muda. A tributação de aluguel mudou em 2026 — não se
aplica mais o desconto simplificado de 20%.

DISCLAIMER: estimativa, não é orientação contábil.

O Carnê-Leão é por CPF: a base é a renda de aluguel total do mês (todos os
apartamentos somados), não por imóvel.
"""
from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.services.domain import DespesaData, ParametrosIR, ReservaData
from app.services.metrics import receita_alocada

ZERO = Decimal("0")


def faixa_aplicavel(base: Decimal, params: ParametrosIR):
    """Maior faixa cujo ``limite_inferior <= base``."""
    faixa = params.faixas[0]
    for f in sorted(params.faixas, key=lambda x: x.limite_inferior):
        if f.limite_inferior <= base:
            faixa = f
        else:
            break
    return faixa


def imposto_bruto(base: Decimal, params: ParametrosIR) -> Decimal:
    """Imposto pela tabela progressiva, antes de isenção/redutor.

    ``imposto_bruto = max(0, base * aliquota - parcela_deduzir)``.
    """
    f = faixa_aplicavel(base, params)
    valor = base * f.aliquota - f.parcela_deduzir
    return valor if valor > 0 else ZERO


def _redutor_transicao(base: Decimal, params: ParametrosIR) -> Decimal:
    """Redutor da faixa de transição 2026 (interpolação linear).

    No ``transicao_inicio`` o redutor zera o imposto; no ``transicao_fim`` o
    redutor é zero. Linear no meio.

    # TODO: confirmar fórmula do redutor 2026 com contador/Receita.
    """
    bruto_inicio = imposto_bruto(params.transicao_inicio, params)
    largura = params.transicao_fim - params.transicao_inicio
    if largura <= 0:
        return ZERO
    fracao = (params.transicao_fim - base) / largura
    if fracao < 0:
        fracao = ZERO
    if fracao > 1:
        fracao = Decimal("1")
    return bruto_inicio * fracao


def imposto_devido_mensal(base: Decimal, params: ParametrosIR) -> Decimal:
    """Imposto devido no mês após isenção efetiva e (opcional) redutor.

    Regras 2026:
      * ``base <= isencao_efetiva`` -> imposto devido = 0 (isento).
      * ``transicao_inicio <= base <= transicao_fim`` -> se
        ``params.aplicar_redutor_transicao`` estiver ativo, aplica redução
        parcial decrescente; caso contrário vale o imposto bruto cheio
        (comportamento "penhasco", que reproduz a planilha validada).
      * ``base > transicao_fim`` -> imposto bruto cheio.
    """
    if base <= params.isencao_efetiva:
        return ZERO

    bruto = imposto_bruto(base, params)

    if (
        params.aplicar_redutor_transicao
        and params.transicao_inicio <= base <= params.transicao_fim
    ):
        devido = bruto - _redutor_transicao(base, params)
        return devido if devido > 0 else ZERO

    return bruto


@dataclass
class LinhaImpostoMensal:
    """Uma linha da grade mensal do imposto."""

    ano: int
    mes: int
    receita_tributavel: Decimal
    despesas_dedutiveis: Decimal
    outras_rendas: Decimal
    base: Decimal
    aliquota: Decimal
    parcela_deduzir: Decimal
    imposto_bruto: Decimal
    isento: bool
    imposto_devido: Decimal


@dataclass
class GradeImposto:
    """Grade anual: 12 linhas + total devido."""

    ano: int
    linhas: list[LinhaImpostoMensal]
    total_devido: Decimal


def _intervalo_mes(ano: int, mes: int) -> tuple[date, date]:
    ultimo = monthrange(ano, mes)[1]
    return date(ano, mes, 1), date(ano, mes, ultimo)


def base_mensal(
    reservas: list[ReservaData],
    despesas: list[DespesaData],
    ano: int,
    mes: int,
    outras_rendas: Decimal = ZERO,
) -> tuple[Decimal, Decimal, Decimal]:
    """Retorna ``(receita_tributavel, despesas_dedutiveis, base)`` do mês.

    * Receita tributável = receita de HOSPEDAGEM alocada por noite no mês
      (todos os apartamentos).
    * Despesas dedutíveis = soma das despesas do mês com ``dedutivel_ir=True``
      (inclui despesas comuns, pois o IR é por CPF).
    * ``base = max(0, receita + outras_rendas - despesas_dedutiveis)``.
    """
    inicio, fim = _intervalo_mes(ano, mes)
    reservas = [r for r in reservas if not r.cancelada]

    receita = sum((receita_alocada(r, inicio, fim) for r in reservas), ZERO)
    ded = sum(
        (
            d.valor
            for d in despesas
            if d.dedutivel_ir and inicio <= d.data <= fim
        ),
        ZERO,
    )
    base = receita + outras_rendas - ded
    if base < 0:
        base = ZERO
    return receita, ded, base


def calcular_grade_imposto(
    reservas: list[ReservaData],
    despesas: list[DespesaData],
    ano: int,
    params: ParametrosIR,
    outras_rendas_por_mes: dict[int, Decimal] | None = None,
) -> GradeImposto:
    """Grade mensal do ano com imposto devido por mês e total anual."""
    outras = outras_rendas_por_mes or {}
    linhas: list[LinhaImpostoMensal] = []
    total = ZERO

    for mes in range(1, 13):
        outras_mes = outras.get(mes, ZERO)
        receita, ded, base = base_mensal(reservas, despesas, ano, mes, outras_mes)
        f = faixa_aplicavel(base, params)
        bruto = imposto_bruto(base, params)
        devido = imposto_devido_mensal(base, params)
        isento = base <= params.isencao_efetiva
        total += devido
        linhas.append(
            LinhaImpostoMensal(
                ano=ano,
                mes=mes,
                receita_tributavel=receita,
                despesas_dedutiveis=ded,
                outras_rendas=outras_mes,
                base=base,
                aliquota=f.aliquota,
                parcela_deduzir=f.parcela_deduzir,
                imposto_bruto=bruto,
                isento=isento,
                imposto_devido=devido,
            )
        )

    return GradeImposto(ano=ano, linhas=linhas, total_devido=total)


def imposto_no_periodo(
    reservas: list[ReservaData],
    despesas: list[DespesaData],
    inicio: date,
    fim: date,
    params: ParametrosIR,
    outras_rendas_por_mes: dict[tuple[int, int], Decimal] | None = None,
) -> Decimal:
    """Soma do imposto devido dos meses que caem em ``[inicio, fim]``.

    Um mês é considerado se seu intervalo intersecta ``[inicio, fim]``.
    """
    outras = outras_rendas_por_mes or {}
    total = ZERO

    ano = inicio.year
    mes = inicio.month
    while (ano, mes) <= (fim.year, fim.month):
        ini_mes, fim_mes = _intervalo_mes(ano, mes)
        if ini_mes <= fim and fim_mes >= inicio:
            outras_mes = outras.get((ano, mes), ZERO)
            _, _, base = base_mensal(reservas, despesas, ano, mes, outras_mes)
            total += imposto_devido_mensal(base, params)
        if mes == 12:
            ano, mes = ano + 1, 1
        else:
            mes += 1

    return total
