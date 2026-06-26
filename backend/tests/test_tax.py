"""Testes da estimativa de IR (Carnê-Leão) — paridade com a planilha."""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.services.tax import (
    base_mensal,
    calcular_grade_imposto,
    imposto_bruto,
    imposto_devido_mensal,
)

D = Decimal


def q2(v: Decimal) -> Decimal:
    return v.quantize(D("0.01"), rounding=ROUND_HALF_UP)


# --------------------------------------------------------------------------- #
# Bases mensais (seção 11)                                                     #
# --------------------------------------------------------------------------- #
def test_base_janeiro(reservas, despesas):
    _, ded, base = base_mensal(reservas, despesas, 2026, 1)
    assert q2(base) == D("5750.00")
    assert q2(ded) == D("1850.00")  # condomínio Copa 650 + Ipanema 1200


def test_base_fevereiro(reservas, despesas):
    _, ded, base = base_mensal(reservas, despesas, 2026, 2)
    assert q2(base) == D("6370.00")
    assert q2(ded) == D("2730.00")  # 650 + 1200 + 380 + 500


def test_base_marco(reservas, despesas):
    _, _, base = base_mensal(reservas, despesas, 2026, 3)
    assert q2(base) == D("4305.00")


# --------------------------------------------------------------------------- #
# Imposto devido mensal (seção 11)                                            #
# --------------------------------------------------------------------------- #
def test_imposto_janeiro(params_ir):
    assert q2(imposto_devido_mensal(D("5750.00"), params_ir)) == D("685.25")


def test_imposto_fevereiro(params_ir):
    assert q2(imposto_devido_mensal(D("6370.00"), params_ir)) == D("855.75")


def test_imposto_marco_isento(params_ir):
    assert imposto_devido_mensal(D("4305.00"), params_ir) == D("0")


def test_grade_anual_total(reservas, despesas, params_ir):
    grade = calcular_grade_imposto(reservas, despesas, 2026, params_ir)
    assert q2(grade.total_devido) == D("1541.00")
    jan = grade.linhas[0]
    assert jan.mes == 1
    assert q2(jan.imposto_devido) == D("685.25")
    assert jan.isento is False
    mar = grade.linhas[2]
    assert mar.isento is True
    assert mar.imposto_devido == D("0")


# --------------------------------------------------------------------------- #
# Casos de borda da isenção (R$ 5.000 vs R$ 5.000,01)                         #
# --------------------------------------------------------------------------- #
def test_base_exatamente_5000_isenta(params_ir):
    assert imposto_devido_mensal(D("5000.00"), params_ir) == D("0")


def test_base_5000_01_nao_isenta(params_ir):
    # Sem redutor (default): imposto cheio mesmo logo acima da isenção.
    bruto = imposto_bruto(D("5000.01"), params_ir)
    assert imposto_devido_mensal(D("5000.01"), params_ir) == bruto
    assert bruto > D("0")


# --------------------------------------------------------------------------- #
# Redutor de transição (opcional, configurável)                              #
# --------------------------------------------------------------------------- #
def test_redutor_transicao_quando_ativo(params_ir):
    p = replace(params_ir, aplicar_redutor_transicao=True)
    # Em transicao_inicio, o redutor zera o imposto.
    assert imposto_devido_mensal(D("5000.01"), p) == D("0")
    # Logo acima da isenção, com redutor ativo, devido < imposto bruto.
    devido = imposto_devido_mensal(D("5750.00"), p)
    bruto = imposto_bruto(D("5750.00"), p)
    assert devido < bruto
    # No fim da transição, redutor zera -> imposto cheio.
    assert q2(imposto_devido_mensal(D("7350.00"), p)) == q2(imposto_bruto(D("7350.00"), p))


def test_faixas_progressivas(params_ir):
    # base na faixa de 7,5%
    assert q2(imposto_bruto(D("2500.00"), params_ir)) == D("18.06")  # 2500*0.075-169.44
    # base na faixa de 27,5%
    assert q2(imposto_bruto(D("5000.00"), params_ir)) == D("479.00")  # 5000*0.275-896
