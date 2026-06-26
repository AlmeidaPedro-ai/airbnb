"""Cálculo de métricas operacionais e financeiras (funções puras).

Nenhuma dependência de banco ou framework: tudo opera sobre as dataclasses de
``app.services.domain``. Dinheiro é sempre :class:`~decimal.Decimal`; o
arredondamento para 2 casas acontece apenas na borda (apresentação).

Convenção de "noite": uma noite pertence à data em que se dorme. A reserva
ocupa as datas ``d`` com ``check_in <= d < check_out`` (a noite do check-out
NÃO conta).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from app.enums import CategoriaDespesa
from app.services.domain import (
    ApartamentoData,
    DespesaData,
    ReservaData,
)

ZERO = Decimal("0")


# --------------------------------------------------------------------------- #
# Primitivas de noite / proração                                              #
# --------------------------------------------------------------------------- #
def noites_no_periodo(
    check_in: date, check_out: date, inicio: date, fim: date
) -> int:
    """Noites de uma reserva que caem dentro de ``[inicio, fim]`` (inclusivo).

    Conta as datas ``d`` tais que ``check_in <= d < check_out`` E
    ``inicio <= d <= fim``. Equivale à interseção do intervalo de ocupação
    ``[check_in, check_out)`` com ``[inicio, fim + 1 dia)``.
    """
    ini = max(check_in, inicio)
    fimx = min(check_out, fim + timedelta(days=1))
    delta = (fimx - ini).days
    return delta if delta > 0 else 0


def _div(numerador: Decimal, denominador: Decimal | int) -> Decimal:
    """Divisão protegida contra divisão por zero (retorna 0)."""
    den = Decimal(denominador)
    if den == 0:
        return ZERO
    return numerador / den


def receita_alocada(reserva: ReservaData, inicio: date, fim: date) -> Decimal:
    """Receita de hospedagem proporcional às noites no período.

    ``receita_alocada = valor_hospedagem * noites_no_periodo / noites_totais``.
    Multiplica antes de dividir para preservar precisão decimal.
    """
    nt = reserva.noites_totais
    if nt <= 0:
        return ZERO
    np = noites_no_periodo(reserva.check_in, reserva.check_out, inicio, fim)
    if np == 0:
        return ZERO
    return reserva.valor_hospedagem * np / Decimal(nt)


def receita_liquida_alocada(
    reserva: ReservaData, inicio: date, fim: date
) -> Decimal:
    """Receita líquida (hospedagem + limpeza - comissão) proporcional às noites."""
    nt = reserva.noites_totais
    if nt <= 0:
        return ZERO
    np = noites_no_periodo(reserva.check_in, reserva.check_out, inicio, fim)
    if np == 0:
        return ZERO
    return reserva.receita_liquida_total * np / Decimal(nt)


def _reservas_ativas(reservas: list[ReservaData]) -> list[ReservaData]:
    """Exclui reservas canceladas dos cálculos de receita/ocupação."""
    return [r for r in reservas if not r.cancelada]


# --------------------------------------------------------------------------- #
# Resultado                                                                    #
# --------------------------------------------------------------------------- #
@dataclass
class MetricasResultado:
    """KPIs agregados de um período. Valores em Decimal (alta precisão)."""

    inicio: date
    fim: date
    dias_no_periodo: int
    num_apartamentos: int

    num_reservas: int
    noites_reservadas: int
    total_hospedes: int
    media_hospedes_por_reserva: Decimal
    los_medio: Decimal

    receita_diarias: Decimal
    receita_liquida_recebida: Decimal
    adr: Decimal

    noites_disponiveis: int
    ocupacao: Decimal
    vacancia: Decimal
    revpar: Decimal

    despesas_totais: Decimal
    despesas_por_categoria: dict[str, Decimal]

    imposto_estimado: Decimal
    lucro_liquido: Decimal


@dataclass
class MetricasApartamento:
    """Recorte por apartamento dentro de um período."""

    apartamento_id: int
    nome: str
    noites: int
    noites_disponiveis: int
    ocupacao: Decimal
    vacancia: Decimal
    hospedes: int
    receita_diarias: Decimal
    adr: Decimal
    despesas: Decimal


# --------------------------------------------------------------------------- #
# Filtros auxiliares                                                           #
# --------------------------------------------------------------------------- #
def _reservas_com_noite(
    reservas: list[ReservaData], inicio: date, fim: date
) -> list[ReservaData]:
    return [
        r
        for r in reservas
        if noites_no_periodo(r.check_in, r.check_out, inicio, fim) > 0
    ]


def _check_in_no_periodo(reserva: ReservaData, inicio: date, fim: date) -> bool:
    return inicio <= reserva.check_in <= fim


def _despesas_no_periodo(
    despesas: list[DespesaData], inicio: date, fim: date
) -> list[DespesaData]:
    return [d for d in despesas if inicio <= d.data <= fim]


# --------------------------------------------------------------------------- #
# Cálculo principal                                                            #
# --------------------------------------------------------------------------- #
def calcular_metricas(
    reservas: list[ReservaData],
    despesas: list[DespesaData],
    inicio: date,
    fim: date,
    num_apartamentos: int,
    imposto_estimado: Decimal = ZERO,
    *,
    noites_disponiveis: int | None = None,
) -> MetricasResultado:
    """Calcula todos os KPIs da seção 4 para um conjunto já filtrado.

    Parâmetros
    ----------
    reservas, despesas:
        Já filtradas pelo escopo desejado (um apê ou todos). Para o filtro
        "Todos" as despesas devem incluir as comuns (``apartamento_id is None``);
        para um apê único, apenas as daquele apê.
    num_apartamentos:
        Quantidade de apartamentos considerados (1 para um apê, ou o total de
        apês ativos para "Todos"). Usado em ``noites_disponiveis`` quando este
        não é informado explicitamente.
    imposto_estimado:
        Imposto do período (calculado em ``services.tax``), subtraído no lucro.
    noites_disponiveis:
        Se informado, usa este valor (ex.: respeitando ``data_inicio_operacao``).
        Caso contrário usa ``dias_no_periodo * num_apartamentos``.
    """
    reservas = _reservas_ativas(reservas)
    dias = (fim - inicio).days + 1

    reservas_periodo = _reservas_com_noite(reservas, inicio, fim)
    num_reservas = len(reservas_periodo)

    noites_reservadas = sum(
        noites_no_periodo(r.check_in, r.check_out, inicio, fim)
        for r in reservas_periodo
    )

    # Total de hóspedes: soma apenas das reservas com CHECK-IN no período, para
    # não contar duas vezes reservas que cruzam a virada de mês.
    total_hospedes = sum(
        r.num_hospedes
        for r in reservas_periodo
        if _check_in_no_periodo(r, inicio, fim)
    )

    receita_diarias = sum(
        (receita_alocada(r, inicio, fim) for r in reservas_periodo), ZERO
    )
    receita_liquida_recebida = sum(
        (receita_liquida_alocada(r, inicio, fim) for r in reservas_periodo),
        ZERO,
    )

    media_hospedes = _div(Decimal(total_hospedes), num_reservas)
    los_medio = _div(Decimal(noites_reservadas), num_reservas)
    adr = _div(receita_diarias, noites_reservadas)

    if noites_disponiveis is None:
        noites_disponiveis = dias * num_apartamentos

    ocupacao = _div(Decimal(noites_reservadas), noites_disponiveis)
    vacancia = (Decimal("1") - ocupacao) if noites_disponiveis else ZERO
    revpar = _div(receita_diarias, noites_disponiveis)

    despesas_periodo = _despesas_no_periodo(despesas, inicio, fim)
    despesas_totais = sum((d.valor for d in despesas_periodo), ZERO)
    por_categoria: dict[str, Decimal] = {}
    for d in despesas_periodo:
        chave = d.categoria.value
        por_categoria[chave] = por_categoria.get(chave, ZERO) + d.valor

    lucro_liquido = receita_liquida_recebida - despesas_totais - imposto_estimado

    return MetricasResultado(
        inicio=inicio,
        fim=fim,
        dias_no_periodo=dias,
        num_apartamentos=num_apartamentos,
        num_reservas=num_reservas,
        noites_reservadas=noites_reservadas,
        total_hospedes=total_hospedes,
        media_hospedes_por_reserva=media_hospedes,
        los_medio=los_medio,
        receita_diarias=receita_diarias,
        receita_liquida_recebida=receita_liquida_recebida,
        adr=adr,
        noites_disponiveis=noites_disponiveis,
        ocupacao=ocupacao,
        vacancia=vacancia,
        revpar=revpar,
        despesas_totais=despesas_totais,
        despesas_por_categoria=por_categoria,
        imposto_estimado=imposto_estimado,
        lucro_liquido=lucro_liquido,
    )


def metricas_por_apartamento(
    apartamentos: list[ApartamentoData],
    reservas: list[ReservaData],
    despesas: list[DespesaData],
    inicio: date,
    fim: date,
    *,
    respeitar_inicio_operacao: bool = False,
) -> list[MetricasApartamento]:
    """KPIs por apartamento ativo no período.

    Despesas comuns (``apartamento_id is None``) NÃO são atribuídas a um apê
    específico nesta visão.
    """
    dias = (fim - inicio).days + 1
    resultado: list[MetricasApartamento] = []

    for apto in apartamentos:
        if not apto.ativo:
            continue
        rsv = [
            r
            for r in _reservas_ativas(reservas)
            if r.apartamento_id == apto.id
        ]
        rsv_periodo = _reservas_com_noite(rsv, inicio, fim)

        noites = sum(
            noites_no_periodo(r.check_in, r.check_out, inicio, fim)
            for r in rsv_periodo
        )
        hospedes = sum(
            r.num_hospedes
            for r in rsv_periodo
            if _check_in_no_periodo(r, inicio, fim)
        )
        receita = sum(
            (receita_alocada(r, inicio, fim) for r in rsv_periodo), ZERO
        )

        if respeitar_inicio_operacao and apto.data_inicio_operacao > inicio:
            inicio_efetivo = max(inicio, apto.data_inicio_operacao)
            disp = (fim - inicio_efetivo).days + 1
            disp = disp if disp > 0 else 0
        else:
            disp = dias

        ocupacao = _div(Decimal(noites), disp)
        despesas_apto = sum(
            (
                d.valor
                for d in _despesas_no_periodo(despesas, inicio, fim)
                if d.apartamento_id == apto.id
            ),
            ZERO,
        )

        resultado.append(
            MetricasApartamento(
                apartamento_id=apto.id,
                nome=apto.nome,
                noites=noites,
                noites_disponiveis=disp,
                ocupacao=ocupacao,
                vacancia=(Decimal("1") - ocupacao) if disp else ZERO,
                hospedes=hospedes,
                receita_diarias=receita,
                adr=_div(receita, noites),
                despesas=despesas_apto,
            )
        )

    return resultado
