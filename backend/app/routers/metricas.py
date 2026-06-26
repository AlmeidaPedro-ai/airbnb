"""Endpoints de métricas operacionais/financeiras."""
from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.business import apartamentos_ativos, get_parametros_ir
from app.deps import CurrentUser, DbSession
from app.models import Despesa, Reserva
from app.schemas import MetricaMensalOut, MetricasApartamentoOut, MetricasOut
from app.services.adapters import (
    apartamento_para_dominio,
    despesa_para_dominio,
    parametros_ir_para_dominio,
    reserva_para_dominio,
)
from app.services.metrics import calcular_metricas, metricas_por_apartamento
from app.services.tax import imposto_no_periodo

router = APIRouter(prefix="/api/metricas", tags=["métricas"])


def _valida_periodo(inicio: date, fim: date) -> None:
    if fim < inicio:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="fim deve ser maior ou igual a inicio.",
        )


def _carregar(db, apartamento_id: int | None):
    """Carrega reservas/despesas/params do escopo e o nº de apês considerados.

    Filtro por apê: só as despesas daquele apê (sem as comuns); Todos: todas as
    despesas (incluindo comuns) e nº de apês ativos.
    """
    reservas_stmt = select(Reserva)
    despesas_stmt = select(Despesa)
    if apartamento_id is not None:
        reservas_stmt = reservas_stmt.where(Reserva.apartamento_id == apartamento_id)
        despesas_stmt = despesas_stmt.where(Despesa.apartamento_id == apartamento_id)
        num_apartamentos = 1
    else:
        num_apartamentos = len(apartamentos_ativos(db))

    reservas = [reserva_para_dominio(r) for r in db.scalars(reservas_stmt).all()]
    despesas = [despesa_para_dominio(d) for d in db.scalars(despesas_stmt).all()]
    params_orm = get_parametros_ir(db, date.today().year)
    params = parametros_ir_para_dominio(params_orm) if params_orm else None
    return reservas, despesas, num_apartamentos, params


@router.get("", response_model=MetricasOut)
def metricas(
    db: DbSession,
    _: CurrentUser,
    inicio: date,
    fim: date,
    apartamento_id: int | None = Query(
        default=None, description="Vazio = todos os apartamentos ativos."
    ),
) -> MetricasOut:
    """KPIs do período. ``apartamento_id`` vazio agrega todos os apês ativos.

    O imposto é calculado sobre o escopo filtrado (todos os apês = base real do
    CPF; um apê = estimativa daquele apê isoladamente).
    """
    _valida_periodo(inicio, fim)
    reservas, despesas, num, params = _carregar(db, apartamento_id)
    params = params if params else None
    # Para o imposto do período, usa os parâmetros do ano do início.
    params_orm = get_parametros_ir(db, inicio.year)
    imposto = (
        imposto_no_periodo(
            reservas, despesas, inicio, fim, parametros_ir_para_dominio(params_orm)
        )
        if params_orm is not None
        else Decimal("0")
    )
    resultado = calcular_metricas(
        reservas, despesas, inicio, fim, num, imposto_estimado=imposto
    )
    return MetricasOut.from_dataclass(resultado)


@router.get("/mensal", response_model=list[MetricaMensalOut])
def mensal(
    db: DbSession,
    _: CurrentUser,
    inicio: date,
    fim: date,
    apartamento_id: int | None = None,
) -> list[MetricaMensalOut]:
    """Série mensal (receita × despesas × imposto) para gráficos.

    Cada mês usa a interseção do mês com ``[inicio, fim]``.
    """
    _valida_periodo(inicio, fim)
    reservas, despesas, num, _params = _carregar(db, apartamento_id)

    serie: list[MetricaMensalOut] = []
    ano, mes = inicio.year, inicio.month
    while (ano, mes) <= (fim.year, fim.month):
        ini_mes = max(inicio, date(ano, mes, 1))
        fim_mes = min(fim, date(ano, mes, monthrange(ano, mes)[1]))
        params_orm = get_parametros_ir(db, ano)
        imposto = (
            imposto_no_periodo(
                reservas, despesas, ini_mes, fim_mes,
                parametros_ir_para_dominio(params_orm),
            )
            if params_orm is not None
            else Decimal("0")
        )
        m = calcular_metricas(
            reservas, despesas, ini_mes, fim_mes, num, imposto_estimado=imposto
        )
        out = MetricasOut.from_dataclass(m)
        serie.append(
            MetricaMensalOut(
                ano=ano,
                mes=mes,
                rotulo=f"{mes:02d}/{ano}",
                noites_reservadas=out.noites_reservadas,
                receita_diarias=out.receita_diarias,
                receita_liquida_recebida=out.receita_liquida_recebida,
                despesas_totais=out.despesas_totais,
                imposto_estimado=out.imposto_estimado,
                ocupacao=out.ocupacao,
            )
        )
        ano, mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)

    return serie


@router.get("/por-apartamento", response_model=list[MetricasApartamentoOut])
def por_apartamento(
    db: DbSession, _: CurrentUser, inicio: date, fim: date
) -> list[MetricasApartamentoOut]:
    """KPIs por apartamento ativo no período."""
    _valida_periodo(inicio, fim)
    apts = [apartamento_para_dominio(a) for a in apartamentos_ativos(db)]
    reservas = [reserva_para_dominio(r) for r in db.scalars(select(Reserva)).all()]
    despesas = [despesa_para_dominio(d) for d in db.scalars(select(Despesa)).all()]
    resultado = metricas_por_apartamento(apts, reservas, despesas, inicio, fim)
    return [MetricasApartamentoOut.from_dataclass(m) for m in resultado]
