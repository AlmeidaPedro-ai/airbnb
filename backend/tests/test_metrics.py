"""Testes das métricas operacionais/financeiras — paridade com a planilha."""
from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import pytest

from app.enums import CategoriaDespesa
from app.services.domain import DespesaData, ReservaData
from app.services.metrics import (
    calcular_metricas,
    metricas_por_apartamento,
    noites_no_periodo,
    receita_alocada,
)
from app.services.tax import imposto_no_periodo

D = Decimal


def q2(v: Decimal) -> Decimal:
    return v.quantize(D("0.01"), rounding=ROUND_HALF_UP)


def q4(v: Decimal) -> Decimal:
    return v.quantize(D("0.0001"), rounding=ROUND_HALF_UP)


# --------------------------------------------------------------------------- #
# Primitivas de noite / proração                                              #
# --------------------------------------------------------------------------- #
def test_noites_simples():
    assert noites_no_periodo(date(2026, 1, 3), date(2026, 1, 7),
                             date(2026, 1, 1), date(2026, 1, 31)) == 4


def test_noite_checkout_nao_conta():
    # Reserva de 1 noite: dorme dia 3, sai dia 4.
    assert noites_no_periodo(date(2026, 1, 3), date(2026, 1, 4),
                             date(2026, 1, 1), date(2026, 1, 31)) == 1


def test_noites_cruza_virada_de_mes():
    # 28/01 -> 03/02: noites 28,29,30,31 (jan) e 01,02 (fev).
    assert noites_no_periodo(date(2026, 1, 28), date(2026, 2, 3),
                             date(2026, 1, 1), date(2026, 1, 31)) == 4
    assert noites_no_periodo(date(2026, 1, 28), date(2026, 2, 3),
                             date(2026, 2, 1), date(2026, 2, 28)) == 2


def test_proracao_receita_cruzando_mes():
    r = ReservaData(1, date(2026, 1, 28), date(2026, 2, 3), 2,
                    D("600"), D("0"), D("0"))
    # 6 noites totais, 4 em janeiro -> 600 * 4/6 = 400.
    assert q2(receita_alocada(r, date(2026, 1, 1), date(2026, 1, 31))) == D("400.00")
    assert q2(receita_alocada(r, date(2026, 2, 1), date(2026, 2, 28))) == D("200.00")


def test_divisao_por_zero_protegida():
    m = calcular_metricas([], [], date(2026, 1, 1), date(2026, 1, 31), 0)
    assert m.adr == D("0")
    assert m.ocupacao == D("0")
    assert m.media_hospedes_por_reserva == D("0")
    assert m.revpar == D("0")


# --------------------------------------------------------------------------- #
# Critérios de aceite — "Todos", 01/01–31/03/2026                             #
# --------------------------------------------------------------------------- #
@pytest.fixture
def metricas_todos(reservas, despesas, params_ir, periodo_q1):
    inicio, fim = periodo_q1
    imposto = imposto_no_periodo(reservas, despesas, inicio, fim, params_ir)
    return calcular_metricas(
        reservas, despesas, inicio, fim,
        num_apartamentos=3, imposto_estimado=imposto,
    )


def test_aceite_contagens(metricas_todos):
    m = metricas_todos
    assert m.num_reservas == 15
    assert m.noites_reservadas == 69
    assert m.total_hospedes == 39


def test_aceite_medias(metricas_todos):
    m = metricas_todos
    assert q2(m.media_hospedes_por_reserva) == D("2.60")
    assert q2(m.los_medio) == D("4.60")


def test_aceite_receitas(metricas_todos):
    m = metricas_todos
    assert q2(m.receita_diarias) == D("22300.00")
    assert q2(m.receita_liquida_recebida) == D("23958.00")
    assert q2(m.adr) == D("323.19")


def test_aceite_ocupacao(metricas_todos):
    m = metricas_todos
    assert m.noites_disponiveis == 270
    assert q4(m.ocupacao) == D("0.2556")
    assert q4(m.vacancia) == D("0.7444")
    assert q2(m.revpar) == D("82.59")


def test_aceite_despesas(metricas_todos):
    m = metricas_todos
    assert q2(m.despesas_totais) == D("8510.00")


def test_aceite_imposto_e_lucro(metricas_todos):
    m = metricas_todos
    assert q2(m.imposto_estimado) == D("1541.00")
    assert q2(m.lucro_liquido) == D("13907.00")


# --------------------------------------------------------------------------- #
# Por apartamento                                                              #
# --------------------------------------------------------------------------- #
def test_aceite_por_apartamento(apartamentos, reservas, despesas, periodo_q1):
    inicio, fim = periodo_q1
    por = {m.nome: m for m in metricas_por_apartamento(
        apartamentos, reservas, despesas, inicio, fim)}

    copa = por["Copacabana 302"]
    assert copa.noites == 25
    assert q4(copa.ocupacao) == D("0.2778")
    assert q2(copa.adr) == D("300.00")
    assert q2(copa.despesas) == D("2520.00")

    ipa = por["Ipanema 1104"]
    assert ipa.noites == 30
    assert q4(ipa.ocupacao) == D("0.3333")
    assert q2(ipa.adr) == D("400.00")
    assert q2(ipa.despesas) == D("4790.00")

    bota = por["Botafogo 506"]
    assert bota.noites == 14
    assert q4(bota.ocupacao) == D("0.1556")
    assert q2(bota.adr) == D("200.00")
    assert q2(bota.despesas) == D("840.00")


# --------------------------------------------------------------------------- #
# Filtro por apê único: despesas comuns NÃO entram                            #
# --------------------------------------------------------------------------- #
def test_filtro_apê_unico_ignora_despesa_comum(reservas, despesas, params_ir):
    inicio, fim = date(2026, 1, 1), date(2026, 3, 31)
    rsv = [r for r in reservas if r.apartamento_id == 1]
    desp = [d for d in despesas if d.apartamento_id == 1]
    m = calcular_metricas(rsv, desp, inicio, fim, num_apartamentos=1)
    # Copacabana: condomínio+luz+limpeza (jan+fev) + IPTU (mar) = 2520, sem internet comum.
    assert q2(m.despesas_totais) == D("2520.00")
    assert m.noites_reservadas == 25


def test_filtro_todos_inclui_despesa_comum(reservas, despesas):
    inicio, fim = date(2026, 1, 1), date(2026, 3, 31)
    m = calcular_metricas(reservas, despesas, inicio, fim, num_apartamentos=3)
    assert "Internet" in m.despesas_por_categoria
    assert q2(m.despesas_por_categoria["Internet"]) == D("360.00")


def test_reserva_cancelada_nao_conta(reservas):
    inicio, fim = date(2026, 1, 1), date(2026, 3, 31)
    canceladas = [
        ReservaData(r.apartamento_id, r.check_in, r.check_out, r.num_hospedes,
                    r.valor_hospedagem, r.taxa_limpeza, r.comissao, cancelada=True)
        for r in reservas
    ]
    m = calcular_metricas(canceladas, [], inicio, fim, num_apartamentos=3)
    assert m.num_reservas == 0
    assert m.receita_diarias == D("0")
