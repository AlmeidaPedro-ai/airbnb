"""Leitura e edição dos parâmetros de IR (só altera o banco, não o código)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.models import FaixaIRDB, ParametroIR
from app.schemas import ParametrosIROut, ParametrosIRUpdate

router = APIRouter(prefix="/api/parametros-ir", tags=["parâmetros-ir"])


def _get_param(db: DbSession, ano: int | None) -> ParametroIR:
    if ano is not None:
        p = db.scalar(select(ParametroIR).where(ParametroIR.ano_vigencia == ano))
    else:
        p = db.scalar(select(ParametroIR).order_by(ParametroIR.ano_vigencia.desc()))
    if p is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parâmetros de IR não encontrados.",
        )
    return p


@router.get("", response_model=ParametrosIROut)
def obter(db: DbSession, _: CurrentUser, ano: int | None = None) -> ParametroIR:
    """Parâmetros do ano informado (ou o mais recente)."""
    return _get_param(db, ano)


@router.put("", response_model=ParametrosIROut)
def atualizar(
    dados: ParametrosIRUpdate,
    db: DbSession,
    _: CurrentUser,
    ano: int | None = None,
) -> ParametroIR:
    """Atualiza parâmetros e (opcionalmente) substitui as faixas por completo."""
    p = _get_param(db, ano)
    campos = dados.model_dump(exclude_unset=True)

    faixas = campos.pop("faixas", None)
    for campo, valor in campos.items():
        setattr(p, campo, valor)

    if faixas is not None:
        if not faixas:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Informe ao menos uma faixa.",
            )
        p.faixas.clear()
        for f in sorted(faixas, key=lambda x: x["limite_inferior"]):
            p.faixas.append(
                FaixaIRDB(
                    limite_inferior=f["limite_inferior"],
                    aliquota=f["aliquota"],
                    parcela_deduzir=f["parcela_deduzir"],
                )
            )

    db.commit()
    db.refresh(p)
    return p
