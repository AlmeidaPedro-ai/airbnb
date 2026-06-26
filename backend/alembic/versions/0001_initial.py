"""schema inicial

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-26
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# create_type=False (postgresql.ENUM): os tipos ENUM são criados/derrubados
# explicitamente em upgrade()/downgrade(); assim create_table não tenta recriá-los.
canal = postgresql.ENUM("Airbnb", "Booking", "Direto", name="canal", create_type=False)
status_reserva = postgresql.ENUM(
    "Confirmada", "Concluída", "Cancelada", name="status_reserva", create_type=False
)
categoria_despesa = postgresql.ENUM(
    "Limpeza", "Luz", "Condomínio", "Gás", "Reparos",
    "IPTU", "Internet", "Seguro", "Outros",
    name="categoria_despesa", create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    canal.create(bind, checkfirst=True)
    status_reserva.create(bind, checkfirst=True)
    categoria_despesa.create(bind, checkfirst=True)

    op.create_table(
        "apartamentos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("endereco", sa.String(255)),
        sa.Column("quartos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("capacidade", sa.Integer(), nullable=False),
        sa.Column("data_inicio_operacao", sa.Date(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("nome", name="uq_apartamentos_nome"),
    )

    op.create_table(
        "reservas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("apartamento_id", sa.Integer(), nullable=False),
        sa.Column("check_in", sa.Date(), nullable=False),
        sa.Column("check_out", sa.Date(), nullable=False),
        sa.Column("num_hospedes", sa.Integer(), nullable=False),
        sa.Column("valor_hospedagem", sa.Numeric(12, 2), nullable=False),
        sa.Column("taxa_limpeza", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("comissao", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("canal", canal, nullable=False, server_default="Airbnb"),
        sa.Column("status", status_reserva, nullable=False, server_default="Confirmada"),
        sa.Column("codigo_confirmacao", sa.String(64)),
        sa.Column("observacao", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["apartamento_id"], ["apartamentos.id"], ondelete="CASCADE"),
        sa.CheckConstraint("check_out > check_in", name="ck_reservas_datas"),
        sa.CheckConstraint("num_hospedes >= 1", name="ck_reservas_hospedes"),
    )
    op.create_index("ix_reservas_apartamento_id", "reservas", ["apartamento_id"])
    op.create_index("ix_reservas_codigo_confirmacao", "reservas", ["codigo_confirmacao"])

    op.create_table(
        "despesas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("apartamento_id", sa.Integer(), nullable=True),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("categoria", categoria_despesa, nullable=False),
        sa.Column("valor", sa.Numeric(12, 2), nullable=False),
        sa.Column("dedutivel_ir", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("recorrente", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("observacao", sa.Text()),
        sa.ForeignKeyConstraint(["apartamento_id"], ["apartamentos.id"], ondelete="CASCADE"),
        sa.CheckConstraint("valor >= 0", name="ck_despesas_valor"),
    )
    op.create_index("ix_despesas_apartamento_id", "despesas", ["apartamento_id"])

    op.create_table(
        "parametros_ir",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ano_vigencia", sa.Integer(), nullable=False),
        sa.Column("isencao_efetiva", sa.Numeric(12, 2), nullable=False),
        sa.Column("transicao_inicio", sa.Numeric(12, 2), nullable=False),
        sa.Column("transicao_fim", sa.Numeric(12, 2), nullable=False),
        sa.Column("aplicar_redutor_transicao", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("ano_vigencia", name="uq_parametros_ir_ano"),
    )

    op.create_table(
        "faixas_ir",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("parametro_id", sa.Integer(), nullable=False),
        sa.Column("limite_inferior", sa.Numeric(12, 2), nullable=False),
        sa.Column("aliquota", sa.Numeric(6, 4), nullable=False),
        sa.Column("parcela_deduzir", sa.Numeric(12, 2), nullable=False),
        sa.ForeignKeyConstraint(["parametro_id"], ["parametros_ir.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("senha_hash", sa.String(255), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_usuarios_email"),
    )


def downgrade() -> None:
    op.drop_table("usuarios")
    op.drop_table("faixas_ir")
    op.drop_table("parametros_ir")
    op.drop_index("ix_despesas_apartamento_id", table_name="despesas")
    op.drop_table("despesas")
    op.drop_index("ix_reservas_codigo_confirmacao", table_name="reservas")
    op.drop_index("ix_reservas_apartamento_id", table_name="reservas")
    op.drop_table("reservas")
    op.drop_table("apartamentos")

    bind = op.get_bind()
    categoria_despesa.drop(bind, checkfirst=True)
    status_reserva.drop(bind, checkfirst=True)
    canal.drop(bind, checkfirst=True)
