"""CRUD de despesas com filtros por apê/categoria/período."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.enums import CategoriaDespesa
from app.models import Apartamento, Despesa
from app.schemas import DespesaCreate, DespesaOut, DespesaUpdate

router = APIRouter(prefix="/api/despesas", tags=["despesas"])


def _checa_apartamento(db: DbSession, apartamento_id: int | None) -> None:
    if apartamento_id is not None and db.get(Apartamento, apartamento_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Apartamento não encontrado.",
        )


@router.get("", response_model=list[DespesaOut])
def listar(
    db: DbSession,
    _: CurrentUser,
    apartamento_id: int | None = None,
    categoria: CategoriaDespesa | None = None,
    inicio: date | None = None,
    fim: date | None = None,
    incluir_comuns: bool = True,
) -> list[Despesa]:
    """Lista despesas. ``apartamento_id`` filtra um apê; ``incluir_comuns``
    adiciona as despesas comuns (apartamento_id nulo) ao resultado."""
    stmt = select(Despesa).order_by(Despesa.data)
    if apartamento_id is not None:
        if incluir_comuns:
            stmt = stmt.where(
                (Despesa.apartamento_id == apartamento_id)
                | (Despesa.apartamento_id.is_(None))
            )
        else:
            stmt = stmt.where(Despesa.apartamento_id == apartamento_id)
    if categoria is not None:
        stmt = stmt.where(Despesa.categoria == categoria)
    if inicio is not None:
        stmt = stmt.where(Despesa.data >= inicio)
    if fim is not None:
        stmt = stmt.where(Despesa.data <= fim)
    return list(db.scalars(stmt).all())


@router.post("", response_model=DespesaOut, status_code=status.HTTP_201_CREATED)
def criar(dados: DespesaCreate, db: DbSession, _: CurrentUser) -> Despesa:
    _checa_apartamento(db, dados.apartamento_id)
    despesa = Despesa(**dados.model_dump())
    db.add(despesa)
    db.commit()
    db.refresh(despesa)
    return despesa


def _get_ou_404(db: DbSession, despesa_id: int) -> Despesa:
    despesa = db.get(Despesa, despesa_id)
    if despesa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Despesa não encontrada."
        )
    return despesa


@router.get("/{despesa_id}", response_model=DespesaOut)
def obter(despesa_id: int, db: DbSession, _: CurrentUser) -> Despesa:
    return _get_ou_404(db, despesa_id)


@router.put("/{despesa_id}", response_model=DespesaOut)
def atualizar(
    despesa_id: int, dados: DespesaUpdate, db: DbSession, _: CurrentUser
) -> Despesa:
    despesa = _get_ou_404(db, despesa_id)
    novos = dados.model_dump(exclude_unset=True)
    if "apartamento_id" in novos:
        _checa_apartamento(db, novos["apartamento_id"])
    for campo, valor in novos.items():
        setattr(despesa, campo, valor)
    db.commit()
    db.refresh(despesa)
    return despesa


@router.delete(
    "/{despesa_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response
)
def remover(despesa_id: int, db: DbSession, _: CurrentUser) -> Response:
    despesa = _get_ou_404(db, despesa_id)
    db.delete(despesa)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
