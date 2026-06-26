"""CRUD de apartamentos."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import CurrentUser, DbSession
from app.models import Apartamento, Despesa, Reserva
from app.schemas import ApartamentoCreate, ApartamentoOut, ApartamentoUpdate

router = APIRouter(prefix="/api/apartamentos", tags=["apartamentos"])


@router.get("", response_model=list[ApartamentoOut])
def listar(
    db: DbSession, _: CurrentUser, apenas_ativos: bool = False
) -> list[Apartamento]:
    stmt = select(Apartamento).order_by(Apartamento.nome)
    if apenas_ativos:
        stmt = stmt.where(Apartamento.ativo.is_(True))
    return list(db.scalars(stmt).all())


@router.post("", response_model=ApartamentoOut, status_code=status.HTTP_201_CREATED)
def criar(dados: ApartamentoCreate, db: DbSession, _: CurrentUser) -> Apartamento:
    apto = Apartamento(**dados.model_dump())
    db.add(apto)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um apartamento com esse nome.",
        )
    db.refresh(apto)
    return apto


def _get_ou_404(db: DbSession, apto_id: int) -> Apartamento:
    apto = db.get(Apartamento, apto_id)
    if apto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Apartamento não encontrado.",
        )
    return apto


@router.get("/{apto_id}", response_model=ApartamentoOut)
def obter(apto_id: int, db: DbSession, _: CurrentUser) -> Apartamento:
    return _get_ou_404(db, apto_id)


@router.put("/{apto_id}", response_model=ApartamentoOut)
def atualizar(
    apto_id: int, dados: ApartamentoUpdate, db: DbSession, _: CurrentUser
) -> Apartamento:
    apto = _get_ou_404(db, apto_id)
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(apto, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um apartamento com esse nome.",
        )
    db.refresh(apto)
    return apto


@router.delete(
    "/{apto_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response
)
def remover(apto_id: int, db: DbSession, _: CurrentUser) -> Response:
    apto = _get_ou_404(db, apto_id)
    tem_reservas = db.scalar(
        select(Reserva.id).where(Reserva.apartamento_id == apto_id).limit(1)
    )
    tem_despesas = db.scalar(
        select(Despesa.id).where(Despesa.apartamento_id == apto_id).limit(1)
    )
    if tem_reservas or tem_despesas:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Apartamento possui reservas/despesas vinculadas. "
                "Em vez de excluir, marque-o como inativo (ativo=false)."
            ),
        )
    db.delete(apto)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
