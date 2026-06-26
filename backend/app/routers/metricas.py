"""Endpoints de métricas operacionais/financeiras."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.business import apartamentos_ativos, get_parametros_ir
from app.deps import CurrentUser, DbSession
from app.models import Despesa, Reserva
from app.schemas import MetricasApartamentoOut, MetricasOut
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

    reservas_stmt = select(Reserva)
    despesas_stmt = select(Despesa)

    if apartamento_id is not None:
        reservas_stmt = reservas_stmt.where(
            Reserva.apartamento_id == apartamento_id
        )
        # Filtro por apê: só despesas daquele apê (sem as comuns).
        despesas_stmt = despesas_stmt.where(
            Despesa.apartamento_id == apartamento_id
        )
        num_apartamentos = 1
    else:
        num_apartamentos = len(apartamentos_ativos(db))

    reservas = [reserva_para_dominio(r) for r in db.scalars(reservas_stmt).all()]
    despesas = [despesa_para_dominio(d) for d in db.scalars(despesas_stmt).all()]

    params_orm = get_parametros_ir(db, inicio.year)
    imposto = (
        imposto_no_periodo(
            reservas, despesas, inicio, fim,
            parametros_ir_para_dominio(params_orm),
        )
        if params_orm is not None
        else None
    )
    resultado = calcular_metricas(
        reservas, despesas, inicio, fim, num_apartamentos,
        imposto_estimado=imposto if imposto is not None else Decimal("0"),
    )
    return MetricasOut.from_dataclass(resultado)


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
