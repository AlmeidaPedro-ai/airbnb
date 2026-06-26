"""Geração de arquivos de exportação (CSV e XLSX).

Funções puras: recebem cabeçalho + linhas (sequências de valores) e devolvem
``bytes``. O router monta as linhas a partir do banco.
"""
from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal
from typing import Any, Sequence

CONTENT_TYPES = {
    "csv": "text/csv; charset=utf-8",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _celula_csv(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "Sim" if v else "Não"
    if isinstance(v, Decimal):
        # Decimal com vírgula decimal (pt-BR) para abrir no Excel BR.
        return format(v, "f").replace(".", ",")
    if isinstance(v, date):
        return v.strftime("%d/%m/%Y")
    return str(v)


def gerar_csv(cabecalho: Sequence[str], linhas: Sequence[Sequence[Any]]) -> bytes:
    """CSV com delimitador ';' (padrão Excel pt-BR) e BOM UTF-8."""
    buf = io.StringIO()
    escritor = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    escritor.writerow(list(cabecalho))
    for linha in linhas:
        escritor.writerow([_celula_csv(v) for v in linha])
    return ("﻿" + buf.getvalue()).encode("utf-8")


def _celula_xlsx(v: Any) -> Any:
    if isinstance(v, bool):
        return "Sim" if v else "Não"
    if isinstance(v, Decimal):
        return float(v)
    return v


def gerar_xlsx(
    cabecalho: Sequence[str],
    linhas: Sequence[Sequence[Any]],
    nome_aba: str = "Dados",
) -> bytes:
    """Planilha XLSX (openpyxl). Datas e números mantêm o tipo nativo."""
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = nome_aba[:31]
    ws.append(list(cabecalho))
    for celula in ws[1]:
        celula.font = Font(bold=True)
    for linha in linhas:
        ws.append([_celula_xlsx(v) for v in linha])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def gerar(
    formato: str,
    cabecalho: Sequence[str],
    linhas: Sequence[Sequence[Any]],
    nome_aba: str = "Dados",
) -> bytes:
    if formato == "csv":
        return gerar_csv(cabecalho, linhas)
    return gerar_xlsx(cabecalho, linhas, nome_aba)
