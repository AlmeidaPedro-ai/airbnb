"""Regras de negócio que dependem do banco (sobreposição, capacidade, etc.).

Mantido separado dos ``services`` puros: aqui podemos consultar a sessão.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.enums import StatusReserva
from app.models import Apartamento, ParametroIR, Reserva


def apartamentos_ativos(db: Session) -> list[Apartamento]:
    return list(
        db.scalars(select(Apartamento).where(Apartamento.ativo.is_(True))).all()
    )


def get_parametros_ir(db: Session, ano: int) -> ParametroIR | None:
    """Parâmetros do ano; se não houver, usa o de maior ``ano_vigencia``."""
    p = db.scalar(select(ParametroIR).where(ParametroIR.ano_vigencia == ano))
    if p is not None:
        return p
    return db.scalar(select(ParametroIR).order_by(ParametroIR.ano_vigencia.desc()))


def reservas_sobrepostas(
    db: Session,
    apartamento_id: int,
    check_in: date,
    check_out: date,
    excluir_id: int | None = None,
) -> list[Reserva]:
    """Reservas não canceladas do mesmo apê cujas datas intersectam o intervalo.

    Sobreposição de ``[check_in, check_out)``: ``a.check_in < novo.check_out``
    E ``a.check_out > novo.check_in``.
    """
    cond = and_(
        Reserva.apartamento_id == apartamento_id,
        Reserva.status != StatusReserva.CANCELADA,
        Reserva.check_in < check_out,
        Reserva.check_out > check_in,
    )
    if excluir_id is not None:
        cond = and_(cond, Reserva.id != excluir_id)
    return list(db.scalars(select(Reserva).where(cond)).all())


def avisos_reserva(
    db: Session,
    apartamento_id: int,
    check_in: date,
    check_out: date,
    num_hospedes: int,
    status: StatusReserva,
    excluir_id: int | None = None,
) -> list[str]:
    """Avisos não bloqueantes: capacidade excedida e sobreposição de datas."""
    avisos: list[str] = []
    apto = db.get(Apartamento, apartamento_id)
    if apto is None:
        return avisos  # erro de FK é tratado na rota

    if num_hospedes > apto.capacidade:
        avisos.append(
            f"Número de hóspedes ({num_hospedes}) excede a capacidade do "
            f"apartamento ({apto.capacidade})."
        )

    if status != StatusReserva.CANCELADA:
        conflitos = reservas_sobrepostas(
            db, apartamento_id, check_in, check_out, excluir_id
        )
        if conflitos:
            datas = ", ".join(
                f"#{r.id} ({r.check_in:%d/%m/%Y}–{r.check_out:%d/%m/%Y})"
                for r in conflitos
            )
            avisos.append(f"Sobreposição de datas com: {datas}.")

    return avisos
