"""Grade mensal de imposto (Carnê-Leão)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.business import get_parametros_ir
from app.deps import CurrentUser, DbSession
from app.models import Despesa, Reserva
from app.schemas import GradeImpostoOut, ImpostoCalcularRequest
from app.services.adapters import (
    despesa_para_dominio,
    parametros_ir_para_dominio,
    reserva_para_dominio,
)
from app.services.tax import calcular_grade_imposto

router = APIRouter(prefix="/api/imposto", tags=["imposto"])


@router.get("", response_model=GradeImpostoOut)
def grade(db: DbSession, _: CurrentUser, ano: int) -> GradeImpostoOut:
    """Grade mensal do ano com base, imposto devido e total anual.

    ``outras_rendas`` ainda não é persistido (default 0); edição mensal chega
    na Fase 3.
    """
    params_orm = get_parametros_ir(db, ano)
    if params_orm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parâmetros de IR não configurados para {ano}.",
        )
    reservas = [reserva_para_dominio(r) for r in db.scalars(select(Reserva)).all()]
    despesas = [despesa_para_dominio(d) for d in db.scalars(select(Despesa)).all()]
    resultado = calcular_grade_imposto(
        reservas, despesas, ano, parametros_ir_para_dominio(params_orm)
    )
    return GradeImpostoOut.from_dataclass(resultado)


@router.post("/calcular", response_model=GradeImpostoOut)
def calcular(
    dados: ImpostoCalcularRequest, db: DbSession, _: CurrentUser
) -> GradeImpostoOut:
    """Recalcula a grade do ano informando 'outras rendas' por mês (1..12)."""
    params_orm = get_parametros_ir(db, dados.ano)
    if params_orm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parâmetros de IR não configurados para {dados.ano}.",
        )
    reservas = [reserva_para_dominio(r) for r in db.scalars(select(Reserva)).all()]
    despesas = [despesa_para_dominio(d) for d in db.scalars(select(Despesa)).all()]
    resultado = calcular_grade_imposto(
        reservas, despesas, dados.ano,
        parametros_ir_para_dominio(params_orm),
        outras_rendas_por_mes=dados.outras_rendas,
    )
    return GradeImpostoOut.from_dataclass(resultado)
