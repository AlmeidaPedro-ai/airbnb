"""Importação de reservas a partir de CSV (ex.: export do Airbnb).

Funções puras: operam sobre listas de dicionários (linhas já lidas do CSV),
sem dependência de banco. O router cuida do upload e da persistência.

O cabeçalho do Airbnb muda com o tempo e por idioma, então o mapeamento de
colunas é sugerido (heurística) e confirmado pelo usuário.
"""
from __future__ import annotations

import csv
import io
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.enums import StatusReserva

# Campos de destino do nosso modelo de reserva.
CAMPOS = [
    "codigo_confirmacao",
    "listing",
    "check_in",
    "check_out",
    "num_hospedes",
    "valor_hospedagem",
    "taxa_limpeza",
    "comissao",
    "status",
]

# Campos obrigatórios para criar uma reserva (listing vira apartamento_id).
OBRIGATORIOS = ["listing", "check_in", "check_out", "num_hospedes", "valor_hospedagem"]

# Palavras-chave (normalizadas) para sugerir o mapeamento de cada campo.
_PALAVRAS: dict[str, list[str]] = {
    "codigo_confirmacao": ["confirmation", "codigo de confirmacao", "cod confirmacao", "codigo"],
    "listing": ["listing", "anuncio", "imovel", "propriedade", "apartamento"],
    "check_in": ["start date", "data de inicio", "check-in", "checkin", "inicio", "entrada"],
    "check_out": ["end date", "data de termino", "data de fim", "check-out", "checkout", "termino", "saida"],
    "num_hospedes": ["of guests", "guests", "hospedes", "adults", "adultos", "no de hospedes"],
    "valor_hospedagem": ["earnings", "ganhos", "valor", "amount", "payout", "bruto"],
    "taxa_limpeza": ["cleaning", "limpeza"],
    "comissao": ["service fee", "host fee", "comissao", "taxa de servico", "taxa"],
    "status": ["status", "situacao"],
}

_FORMATOS_DATA = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%d/%m/%y",
    "%m/%d/%y",
]


def normalizar(texto: str) -> str:
    """Minúsculas, sem acentos e sem espaços nas bordas."""
    s = unicodedata.normalize("NFKD", texto)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().lower()


def ler_csv(conteudo: str) -> tuple[list[str], list[dict[str, str]]]:
    """Lê o CSV (auto-detecta delimitador , ou ;) e devolve (colunas, linhas)."""
    amostra = conteudo[:4096]
    try:
        dialeto = csv.Sniffer().sniff(amostra, delimiters=",;\t")
    except csv.Error:
        dialeto = csv.excel
    leitor = csv.DictReader(io.StringIO(conteudo), dialect=dialeto)
    colunas = [c.strip() for c in (leitor.fieldnames or [])]
    linhas = [
        {(k.strip() if k else k): (v or "").strip() for k, v in linha.items()}
        for linha in leitor
    ]
    return colunas, linhas


def sugerir_mapeamento(colunas: list[str]) -> dict[str, str | None]:
    """Sugere, para cada campo de destino, a coluna do CSV mais provável."""
    norm = {c: normalizar(c) for c in colunas}
    usados: set[str] = set()
    sugestao: dict[str, str | None] = {}
    for campo in CAMPOS:
        escolha: str | None = None
        for palavra in _PALAVRAS[campo]:
            for col in colunas:
                if col in usados:
                    continue
                if palavra in norm[col]:
                    escolha = col
                    break
            if escolha:
                break
        if escolha:
            usados.add(escolha)
        sugestao[campo] = escolha
    return sugestao


def extrair_listings(
    linhas: list[dict[str, str]], coluna_listing: str | None
) -> list[str]:
    """Valores distintos da coluna de anúncio/listing (para o de-para)."""
    if not coluna_listing:
        return []
    vistos: list[str] = []
    for linha in linhas:
        v = (linha.get(coluna_listing) or "").strip()
        if v and v not in vistos:
            vistos.append(v)
    return vistos


def parse_data(valor: str) -> date | None:
    valor = valor.strip()
    if not valor:
        return None
    for fmt in _FORMATOS_DATA:
        try:
            return datetime.strptime(valor, fmt).date()
        except ValueError:
            continue
    return None


def parse_dinheiro(valor: str) -> Decimal | None:
    """Converte texto monetário (BR ou US) em Decimal. Vazio -> 0."""
    s = "".join(ch for ch in valor if ch.isdigit() or ch in ",.-")
    if not s or s in {"-", ".", ","}:
        return Decimal("0") if valor.strip() == "" else None
    try:
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):  # vírgula decimal (BR): 1.200,00
                s = s.replace(".", "").replace(",", ".")
            else:  # ponto decimal (US): 1,200.00
                s = s.replace(",", "")
        elif "," in s:
            partes = s.split(",")
            if len(partes) == 2 and len(partes[1]) in (1, 2):
                s = s.replace(",", ".")  # decimal
            else:
                s = s.replace(",", "")  # milhar
        return Decimal(s)
    except InvalidOperation:
        return None


def parse_status(valor: str) -> StatusReserva:
    n = normalizar(valor)
    if any(p in n for p in ["cancel"]):
        return StatusReserva.CANCELADA
    if any(p in n for p in ["past", "complet", "conclu", "checked out", "finaliz"]):
        return StatusReserva.CONCLUIDA
    return StatusReserva.CONFIRMADA


@dataclass
class LinhaImportada:
    """Resultado do processamento de uma linha do CSV."""

    indice: int  # nº da linha (1-based, sem o cabeçalho)
    acao: str  # "criar" | "ignorar" | "erro"
    motivo: str | None = None
    # Dados já convertidos (presentes quando acao == "criar").
    apartamento_id: int | None = None
    listing: str | None = None
    codigo_confirmacao: str | None = None
    check_in: date | None = None
    check_out: date | None = None
    num_hospedes: int | None = None
    valor_hospedagem: Decimal | None = None
    taxa_limpeza: Decimal = Decimal("0")
    comissao: Decimal = Decimal("0")
    status: StatusReserva = StatusReserva.CONFIRMADA


@dataclass
class PreviaImportacao:
    """Resumo do dry-run / importação."""

    linhas: list[LinhaImportada] = field(default_factory=list)
    total: int = 0
    criar: int = 0
    ignorar: int = 0
    erro: int = 0


def processar(
    linhas: list[dict[str, str]],
    mapeamento: dict[str, str | None],
    de_para: dict[str, int],
    codigos_existentes: set[str],
) -> PreviaImportacao:
    """Aplica mapeamento + de-para, deduplica e valida cada linha.

    Parâmetros
    ----------
    mapeamento: campo de destino -> nome da coluna no CSV (ou None).
    de_para: valor do listing -> apartamento_id.
    codigos_existentes: códigos de confirmação já no banco (dedup).
    """
    previa = PreviaImportacao(total=len(linhas))
    vistos_no_arquivo: set[str] = set()

    def col(campo: str, linha: dict[str, str]) -> str:
        coluna = mapeamento.get(campo)
        return (linha.get(coluna, "") if coluna else "").strip()

    for i, linha in enumerate(linhas, start=1):
        codigo = col("codigo_confirmacao", linha) or None

        # Dedup por código de confirmação (banco e dentro do próprio arquivo).
        if codigo and (codigo in codigos_existentes or codigo in vistos_no_arquivo):
            previa.linhas.append(
                LinhaImportada(i, "ignorar", "Código de confirmação já existe",
                               codigo_confirmacao=codigo)
            )
            previa.ignorar += 1
            continue

        listing = col("listing", linha) or None
        ci = parse_data(col("check_in", linha))
        co = parse_data(col("check_out", linha))
        hosp_txt = col("num_hospedes", linha)
        valor = parse_dinheiro(col("valor_hospedagem", linha))

        erros: list[str] = []
        apartamento_id = de_para.get(listing) if listing else None
        if not listing:
            erros.append("Anúncio (listing) ausente")
        elif apartamento_id is None:
            erros.append(f"Anúncio '{listing}' não associado a um apartamento")
        if ci is None:
            erros.append("Data de check-in inválida")
        if co is None:
            erros.append("Data de check-out inválida")
        if ci and co and co <= ci:
            erros.append("check-out deve ser posterior ao check-in")
        try:
            num_hospedes = int(float(hosp_txt)) if hosp_txt else 0
        except ValueError:
            num_hospedes = 0
        if num_hospedes < 1:
            erros.append("Nº de hóspedes inválido")
        if valor is None:
            erros.append("Valor de hospedagem inválido")

        if erros:
            previa.linhas.append(
                LinhaImportada(i, "erro", "; ".join(erros), listing=listing,
                               codigo_confirmacao=codigo)
            )
            previa.erro += 1
            continue

        if codigo:
            vistos_no_arquivo.add(codigo)

        previa.linhas.append(
            LinhaImportada(
                indice=i,
                acao="criar",
                apartamento_id=apartamento_id,
                listing=listing,
                codigo_confirmacao=codigo,
                check_in=ci,
                check_out=co,
                num_hospedes=num_hospedes,
                valor_hospedagem=valor,
                taxa_limpeza=parse_dinheiro(col("taxa_limpeza", linha)) or Decimal("0"),
                comissao=parse_dinheiro(col("comissao", linha)) or Decimal("0"),
                status=parse_status(col("status", linha)),
            )
        )
        previa.criar += 1

    return previa
