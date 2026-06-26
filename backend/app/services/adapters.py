"""Conversão de modelos ORM para as dataclasses puras de domínio."""
from __future__ import annotations

from app.enums import StatusReserva
from app.models import Apartamento, Despesa, ParametroIR, Reserva
from app.services.domain import (
    ApartamentoData,
    DespesaData,
    FaixaIR,
    ParametrosIR,
    ReservaData,
)


def apartamento_para_dominio(a: Apartamento) -> ApartamentoData:
    return ApartamentoData(
        id=a.id,
        nome=a.nome,
        data_inicio_operacao=a.data_inicio_operacao,
        ativo=a.ativo,
    )


def reserva_para_dominio(r: Reserva) -> ReservaData:
    return ReservaData(
        apartamento_id=r.apartamento_id,
        check_in=r.check_in,
        check_out=r.check_out,
        num_hospedes=r.num_hospedes,
        valor_hospedagem=r.valor_hospedagem,
        taxa_limpeza=r.taxa_limpeza,
        comissao=r.comissao,
        cancelada=(r.status == StatusReserva.CANCELADA),
    )


def despesa_para_dominio(d: Despesa) -> DespesaData:
    return DespesaData(
        apartamento_id=d.apartamento_id,
        data=d.data,
        categoria=d.categoria,
        valor=d.valor,
        dedutivel_ir=d.dedutivel_ir,
    )


def parametros_ir_para_dominio(p: ParametroIR) -> ParametrosIR:
    return ParametrosIR(
        ano_vigencia=p.ano_vigencia,
        faixas=[
            FaixaIR(
                limite_inferior=f.limite_inferior,
                aliquota=f.aliquota,
                parcela_deduzir=f.parcela_deduzir,
            )
            for f in p.faixas
        ],
        isencao_efetiva=p.isencao_efetiva,
        transicao_inicio=p.transicao_inicio,
        transicao_fim=p.transicao_fim,
        aplicar_redutor_transicao=p.aplicar_redutor_transicao,
    )
