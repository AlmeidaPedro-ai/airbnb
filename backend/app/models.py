"""Modelos SQLAlchemy 2.0. Dinheiro sempre em ``NUMERIC(12,2)``."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import Canal, CategoriaDespesa, StatusReserva

MONEY = Numeric(12, 2)


def _enum(py_enum, name: str) -> SAEnum:
    """Enum nativo do Postgres que persiste o VALUE legível (ex.: 'Condomínio'),
    não o nome do membro (ex.: 'CONDOMINIO'). Mantém paridade com a migração."""
    return SAEnum(
        py_enum,
        name=name,
        values_callable=lambda e: [m.value for m in e],
    )


class Apartamento(Base):
    __tablename__ = "apartamentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    endereco: Mapped[str | None] = mapped_column(String(255))
    quartos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    capacidade: Mapped[int] = mapped_column(Integer, nullable=False)
    data_inicio_operacao: Mapped[date] = mapped_column(Date, nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    reservas: Mapped[list["Reserva"]] = relationship(back_populates="apartamento")
    despesas: Mapped[list["Despesa"]] = relationship(back_populates="apartamento")


class Reserva(Base):
    __tablename__ = "reservas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    apartamento_id: Mapped[int] = mapped_column(
        ForeignKey("apartamentos.id", ondelete="CASCADE"), nullable=False
    )
    check_in: Mapped[date] = mapped_column(Date, nullable=False)
    check_out: Mapped[date] = mapped_column(Date, nullable=False)
    num_hospedes: Mapped[int] = mapped_column(Integer, nullable=False)
    valor_hospedagem: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    taxa_limpeza: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    comissao: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    canal: Mapped[Canal] = mapped_column(
        _enum(Canal, "canal"), default=Canal.AIRBNB, nullable=False
    )
    status: Mapped[StatusReserva] = mapped_column(
        _enum(StatusReserva, "status_reserva"),
        default=StatusReserva.CONFIRMADA,
        nullable=False,
    )
    codigo_confirmacao: Mapped[str | None] = mapped_column(String(64), index=True)
    observacao: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    apartamento: Mapped[Apartamento] = relationship(back_populates="reservas")


class Despesa(Base):
    __tablename__ = "despesas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # nullable => despesa comum (rateada/geral)
    apartamento_id: Mapped[int | None] = mapped_column(
        ForeignKey("apartamentos.id", ondelete="CASCADE"), nullable=True
    )
    data: Mapped[date] = mapped_column(Date, nullable=False)
    categoria: Mapped[CategoriaDespesa] = mapped_column(
        _enum(CategoriaDespesa, "categoria_despesa"), nullable=False
    )
    valor: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    dedutivel_ir: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recorrente: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    observacao: Mapped[str | None] = mapped_column(Text)

    apartamento: Mapped[Apartamento | None] = relationship(back_populates="despesas")


class ParametroIR(Base):
    """Parâmetros tributários versionados por ano (faixas em JSON)."""

    __tablename__ = "parametros_ir"
    __table_args__ = (UniqueConstraint("ano_vigencia", name="uq_parametros_ir_ano"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ano_vigencia: Mapped[int] = mapped_column(Integer, nullable=False)
    isencao_efetiva: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    transicao_inicio: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    transicao_fim: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    aplicar_redutor_transicao: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    faixas: Mapped[list["FaixaIRDB"]] = relationship(
        back_populates="parametro",
        cascade="all, delete-orphan",
        order_by="FaixaIRDB.limite_inferior",
    )


class FaixaIRDB(Base):
    __tablename__ = "faixas_ir"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parametro_id: Mapped[int] = mapped_column(
        ForeignKey("parametros_ir.id", ondelete="CASCADE"), nullable=False
    )
    limite_inferior: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    aliquota: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    parcela_deduzir: Mapped[Decimal] = mapped_column(MONEY, nullable=False)

    parametro: Mapped[ParametroIR] = relationship(back_populates="faixas")


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
