"""Popula o banco com o dataset canônico da seção 11 e os parâmetros de IR.

Idempotente: não duplica se já existir um apartamento com o mesmo nome.
Uso: ``python -m app.seed``
"""
from __future__ import annotations

import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.enums import Canal, StatusReserva
from app.models import (
    Apartamento,
    Despesa,
    FaixaIRDB,
    ParametroIR,
    Reserva,
    Usuario,
)
from app.seed_data import (
    APARTAMENTOS,
    APARTAMENTOS_META,
    DESPESAS,
    RESERVAS,
    RESERVAS_CANAL,
    parametros_ir_2026,
)


def _seed_parametros_ir(db: Session) -> None:
    p = parametros_ir_2026()
    existente = db.scalar(
        select(ParametroIR).where(ParametroIR.ano_vigencia == p.ano_vigencia)
    )
    if existente:
        return
    param = ParametroIR(
        ano_vigencia=p.ano_vigencia,
        isencao_efetiva=p.isencao_efetiva,
        transicao_inicio=p.transicao_inicio,
        transicao_fim=p.transicao_fim,
        aplicar_redutor_transicao=p.aplicar_redutor_transicao,
        faixas=[
            FaixaIRDB(
                limite_inferior=f.limite_inferior,
                aliquota=f.aliquota,
                parcela_deduzir=f.parcela_deduzir,
            )
            for f in p.faixas
        ],
    )
    db.add(param)


def _seed_usuario(db: Session) -> None:
    if db.scalar(select(Usuario).limit(1)):
        return
    from app.security import hash_senha

    email = os.getenv("SEED_USER_EMAIL", "1994.pedro@gmail.com")
    senha = os.getenv("SEED_USER_PASSWORD", "admin123")
    db.add(Usuario(email=email, senha_hash=hash_senha(senha), ativo=True))


def seed(db: Session) -> dict[str, int]:
    """Executa o seed completo. Retorna contagens criadas."""
    _seed_parametros_ir(db)
    _seed_usuario(db)

    criados_apto = 0
    id_map: dict[int, int] = {}  # id do seed_data -> id real no banco
    for a in APARTAMENTOS:
        existente = db.scalar(select(Apartamento).where(Apartamento.nome == a.nome))
        if existente:
            id_map[a.id] = existente.id
            continue
        meta = APARTAMENTOS_META[a.id]
        apto = Apartamento(
            nome=a.nome,
            endereco=meta["endereco"],
            quartos=meta["quartos"],
            capacidade=meta["capacidade"],
            data_inicio_operacao=a.data_inicio_operacao,
            ativo=a.ativo,
        )
        db.add(apto)
        db.flush()
        id_map[a.id] = apto.id
        criados_apto += 1

    criados_reserva = 0
    # Só insere reservas se ainda não houver nenhuma (evita duplicar).
    if not db.scalar(select(Reserva).limit(1)):
        for r, canal in zip(RESERVAS, RESERVAS_CANAL):
            db.add(
                Reserva(
                    apartamento_id=id_map[r.apartamento_id],
                    check_in=r.check_in,
                    check_out=r.check_out,
                    num_hospedes=r.num_hospedes,
                    valor_hospedagem=r.valor_hospedagem,
                    taxa_limpeza=r.taxa_limpeza,
                    comissao=r.comissao,
                    canal=Canal(canal),
                    status=StatusReserva.CONFIRMADA,
                )
            )
            criados_reserva += 1

    criados_despesa = 0
    if not db.scalar(select(Despesa).limit(1)):
        for d in DESPESAS:
            db.add(
                Despesa(
                    apartamento_id=id_map[d.apartamento_id] if d.apartamento_id else None,
                    data=d.data,
                    categoria=d.categoria,
                    valor=d.valor,
                    dedutivel_ir=d.dedutivel_ir,
                )
            )
            criados_despesa += 1

    db.commit()
    return {
        "apartamentos": criados_apto,
        "reservas": criados_reserva,
        "despesas": criados_despesa,
    }


def main() -> None:
    db = SessionLocal()
    try:
        resultado = seed(db)
        print(f"Seed concluído: {resultado}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
