"""Importação de reservas via CSV (análise + confirmação com dry-run)."""
from __future__ import annotations

import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.enums import Canal
from app.models import Reserva
from app.schemas import (
    ImportarAnaliseOut,
    LinhaImportadaOut,
    PreviaImportacaoOut,
)
from app.services import importacao

router = APIRouter(prefix="/api/importar", tags=["importação"])


async def _ler_conteudo(arquivo: UploadFile) -> str:
    bruto = await arquivo.read()
    for codec in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return bruto.decode(codec)
        except UnicodeDecodeError:
            continue
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Não foi possível decodificar o arquivo (use UTF-8).",
    )


def _parse_json_form(nome: str, valor: str) -> dict:
    try:
        dados = json.loads(valor)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Campo '{nome}' não é um JSON válido.",
        )
    if not isinstance(dados, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Campo '{nome}' deve ser um objeto JSON.",
        )
    return dados


@router.post("/reservas/analisar", response_model=ImportarAnaliseOut)
async def analisar(
    _: CurrentUser, arquivo: UploadFile = File(...)
) -> ImportarAnaliseOut:
    """Lê o CSV e devolve colunas, mapeamento sugerido e os anúncios (listings)."""
    conteudo = await _ler_conteudo(arquivo)
    colunas, linhas = importacao.ler_csv(conteudo)
    if not colunas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV sem cabeçalho reconhecível.",
        )
    sugestao = importacao.sugerir_mapeamento(colunas)
    listings = importacao.extrair_listings(linhas, sugestao.get("listing"))
    return ImportarAnaliseOut(
        colunas=colunas,
        campos=importacao.CAMPOS,
        obrigatorios=importacao.OBRIGATORIOS,
        sugestao_mapeamento=sugestao,
        listings=listings,
        amostra=linhas[:5],
        total_linhas=len(linhas),
    )


@router.post("/reservas/confirmar", response_model=PreviaImportacaoOut)
async def confirmar(
    db: DbSession,
    _: CurrentUser,
    arquivo: UploadFile = File(...),
    mapeamento: str = Form(..., description="JSON: campo -> coluna do CSV"),
    de_para: str = Form(..., description="JSON: listing -> apartamento_id"),
    dry_run: bool = Form(True),
) -> PreviaImportacaoOut:
    """Dry-run (default) ou importação efetiva das reservas do CSV."""
    conteudo = await _ler_conteudo(arquivo)
    _colunas, linhas = importacao.ler_csv(conteudo)

    mapa = {k: (v or None) for k, v in _parse_json_form("mapeamento", mapeamento).items()}
    dp_bruto = _parse_json_form("de_para", de_para)
    try:
        dp = {str(k): int(v) for k, v in dp_bruto.items()}
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="de_para deve mapear listing -> apartamento_id (inteiro).",
        )

    codigos = {
        c
        for (c,) in db.execute(
            select(Reserva.codigo_confirmacao).where(
                Reserva.codigo_confirmacao.is_not(None)
            )
        ).all()
    }

    previa = importacao.processar(linhas, mapa, dp, codigos)

    importadas = 0
    if not dry_run:
        for l in previa.linhas:
            if l.acao != "criar":
                continue
            db.add(
                Reserva(
                    apartamento_id=l.apartamento_id,
                    check_in=l.check_in,
                    check_out=l.check_out,
                    num_hospedes=l.num_hospedes,
                    valor_hospedagem=l.valor_hospedagem,
                    taxa_limpeza=l.taxa_limpeza,
                    comissao=l.comissao,
                    canal=Canal.AIRBNB,
                    status=l.status,
                    codigo_confirmacao=l.codigo_confirmacao,
                )
            )
            importadas += 1
        db.commit()

    return PreviaImportacaoOut(
        dry_run=dry_run,
        total=previa.total,
        criar=previa.criar,
        ignorar=previa.ignorar,
        erro=previa.erro,
        importadas=importadas,
        linhas=[LinhaImportadaOut.from_dataclass(l) for l in previa.linhas],
    )
