"""Exportação de reservas, despesas e grade de imposto (CSV / XLSX)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select

from app.business import get_parametros_ir
from app.deps import CurrentUser, DbSession
from app.enums import CategoriaDespesa
from app.models import Apartamento, Despesa, Reserva
from app.services.adapters import (
    despesa_para_dominio,
    parametros_ir_para_dominio,
    reserva_para_dominio,
)
from app.services.exportacao import CONTENT_TYPES, gerar
from app.services.tax import calcular_grade_imposto

router = APIRouter(prefix="/api/exportar", tags=["exportação"])

NOMES_MES = [
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
]


def _resposta(formato: str, nome: str, cabecalho, linhas, aba: str) -> Response:
    if formato not in CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="formato deve ser 'csv' ou 'xlsx'.",
        )
    conteudo = gerar(formato, cabecalho, linhas, aba)
    return Response(
        content=conteudo,
        media_type=CONTENT_TYPES[formato],
        headers={
            "Content-Disposition": f'attachment; filename="{nome}.{formato}"'
        },
    )


def _nomes_apartamentos(db) -> dict[int, str]:
    return {a.id: a.nome for a in db.scalars(select(Apartamento)).all()}


@router.get("/reservas")
def exportar_reservas(
    db: DbSession,
    _: CurrentUser,
    formato: str = Query("csv"),
    apartamento_id: int | None = None,
    inicio: date | None = None,
    fim: date | None = None,
) -> Response:
    stmt = select(Reserva).order_by(Reserva.check_in)
    if apartamento_id is not None:
        stmt = stmt.where(Reserva.apartamento_id == apartamento_id)
    if inicio is not None:
        stmt = stmt.where(Reserva.check_out > inicio)
    if fim is not None:
        stmt = stmt.where(Reserva.check_in <= fim)

    nomes = _nomes_apartamentos(db)
    cabecalho = [
        "ID", "Apartamento", "Check-in", "Check-out", "Noites", "Hóspedes",
        "Hospedagem", "Taxa limpeza", "Comissão", "Receita líquida",
        "Canal", "Status", "Código confirmação",
    ]
    linhas = []
    for r in db.scalars(stmt).all():
        d = reserva_para_dominio(r)
        linhas.append([
            r.id,
            nomes.get(r.apartamento_id, ""),
            r.check_in,
            r.check_out,
            d.noites_totais,
            r.num_hospedes,
            r.valor_hospedagem,
            r.taxa_limpeza,
            r.comissao,
            d.receita_liquida_total,
            r.canal.value,
            r.status.value,
            r.codigo_confirmacao or "",
        ])
    return _resposta(formato, "reservas", cabecalho, linhas, "Reservas")


@router.get("/despesas")
def exportar_despesas(
    db: DbSession,
    _: CurrentUser,
    formato: str = Query("csv"),
    apartamento_id: int | None = None,
    categoria: CategoriaDespesa | None = None,
    inicio: date | None = None,
    fim: date | None = None,
) -> Response:
    stmt = select(Despesa).order_by(Despesa.data)
    if apartamento_id is not None:
        stmt = stmt.where(Despesa.apartamento_id == apartamento_id)
    if categoria is not None:
        stmt = stmt.where(Despesa.categoria == categoria)
    if inicio is not None:
        stmt = stmt.where(Despesa.data >= inicio)
    if fim is not None:
        stmt = stmt.where(Despesa.data <= fim)

    nomes = _nomes_apartamentos(db)
    cabecalho = [
        "ID", "Data", "Apartamento", "Categoria", "Valor",
        "Dedutível IR", "Recorrente", "Observação",
    ]
    linhas = [
        [
            d.id,
            d.data,
            nomes.get(d.apartamento_id, "Comum / geral") if d.apartamento_id else "Comum / geral",
            d.categoria.value,
            d.valor,
            d.dedutivel_ir,
            d.recorrente,
            d.observacao or "",
        ]
        for d in db.scalars(stmt).all()
    ]
    return _resposta(formato, "despesas", cabecalho, linhas, "Despesas")


@router.get("/imposto")
def exportar_imposto(
    db: DbSession, _: CurrentUser, ano: int, formato: str = Query("csv")
) -> Response:
    params_orm = get_parametros_ir(db, ano)
    if params_orm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parâmetros de IR não configurados para {ano}.",
        )
    reservas = [reserva_para_dominio(r) for r in db.scalars(select(Reserva)).all()]
    despesas = [despesa_para_dominio(d) for d in db.scalars(select(Despesa)).all()]
    grade = calcular_grade_imposto(
        reservas, despesas, ano, parametros_ir_para_dominio(params_orm)
    )

    cabecalho = [
        "Mês", "Receita tributável", "Despesas dedutíveis", "Outras rendas",
        "Base", "Alíquota %", "Parcela deduzir", "Imposto bruto",
        "Isento", "Imposto devido",
    ]
    linhas = [
        [
            NOMES_MES[l.mes - 1],
            l.receita_tributavel,
            l.despesas_dedutiveis,
            l.outras_rendas,
            l.base,
            l.aliquota * Decimal("100"),
            l.parcela_deduzir,
            l.imposto_bruto,
            l.isento,
            l.imposto_devido,
        ]
        for l in grade.linhas
    ]
    linhas.append(
        ["Total", "", "", "", "", "", "", "", "", grade.total_devido]
    )
    return _resposta(formato, f"imposto_{ano}", cabecalho, linhas, f"Imposto {ano}")
