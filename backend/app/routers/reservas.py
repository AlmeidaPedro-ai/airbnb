"""CRUD de reservas com filtros e avisos de negócio."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.business import avisos_reserva
from app.deps import CurrentUser, DbSession
from app.models import Apartamento, Reserva
from app.schemas import ReservaCreate, ReservaOut, ReservaResult, ReservaUpdate

router = APIRouter(prefix="/api/reservas", tags=["reservas"])


def _checa_apartamento(db: DbSession, apartamento_id: int) -> None:
    if db.get(Apartamento, apartamento_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Apartamento não encontrado.",
        )


@router.get("", response_model=list[ReservaOut])
def listar(
    db: DbSession,
    _: CurrentUser,
    apartamento_id: int | None = None,
    inicio: date | None = None,
    fim: date | None = None,
) -> list[Reserva]:
    """Lista reservas. Filtro por período = reservas que se sobrepõem a ele."""
    stmt = select(Reserva).order_by(Reserva.check_in)
    if apartamento_id is not None:
        stmt = stmt.where(Reserva.apartamento_id == apartamento_id)
    if inicio is not None:
        stmt = stmt.where(Reserva.check_out > inicio)
    if fim is not None:
        stmt = stmt.where(Reserva.check_in <= fim)
    return list(db.scalars(stmt).all())


@router.post("", response_model=ReservaResult, status_code=status.HTTP_201_CREATED)
def criar(dados: ReservaCreate, db: DbSession, _: CurrentUser) -> ReservaResult:
    _checa_apartamento(db, dados.apartamento_id)
    avisos = avisos_reserva(
        db, dados.apartamento_id, dados.check_in, dados.check_out,
        dados.num_hospedes, dados.status,
    )
    reserva = Reserva(**dados.model_dump())
    db.add(reserva)
    db.commit()
    db.refresh(reserva)
    return ReservaResult(reserva=ReservaOut.model_validate(reserva), avisos=avisos)


def _get_ou_404(db: DbSession, reserva_id: int) -> Reserva:
    reserva = db.get(Reserva, reserva_id)
    if reserva is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reserva não encontrada."
        )
    return reserva


@router.get("/{reserva_id}", response_model=ReservaOut)
def obter(reserva_id: int, db: DbSession, _: CurrentUser) -> Reserva:
    return _get_ou_404(db, reserva_id)


@router.put("/{reserva_id}", response_model=ReservaResult)
def atualizar(
    reserva_id: int, dados: ReservaUpdate, db: DbSession, _: CurrentUser
) -> ReservaResult:
    reserva = _get_ou_404(db, reserva_id)
    novos = dados.model_dump(exclude_unset=True)
    if "apartamento_id" in novos:
        _checa_apartamento(db, novos["apartamento_id"])
    for campo, valor in novos.items():
        setattr(reserva, campo, valor)
    if reserva.check_out <= reserva.check_in:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="check_out deve ser posterior a check_in.",
        )
    avisos = avisos_reserva(
        db, reserva.apartamento_id, reserva.check_in, reserva.check_out,
        reserva.num_hospedes, reserva.status, excluir_id=reserva.id,
    )
    db.commit()
    db.refresh(reserva)
    return ReservaResult(reserva=ReservaOut.model_validate(reserva), avisos=avisos)


@router.delete(
    "/{reserva_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response
)
def remover(reserva_id: int, db: DbSession, _: CurrentUser) -> Response:
    reserva = _get_ou_404(db, reserva_id)
    db.delete(reserva)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
