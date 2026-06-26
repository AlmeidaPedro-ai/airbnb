"""Dataset canônico de exemplo (seção 11 — paridade com a planilha validada).

Fonte única usada tanto pelo seed do banco quanto pelos testes pytest. Os
valores monetários estão em :class:`~decimal.Decimal`. Todas as datas são de
2026.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.enums import CategoriaDespesa
from app.services.domain import (
    ApartamentoData,
    DespesaData,
    FaixaIR,
    ParametrosIR,
    ReservaData,
)

D = Decimal


# --------------------------------------------------------------------------- #
# Apartamentos                                                                 #
# --------------------------------------------------------------------------- #
APARTAMENTOS: list[ApartamentoData] = [
    ApartamentoData(1, "Copacabana 302", date(2026, 1, 1)),
    ApartamentoData(2, "Ipanema 1104", date(2026, 1, 1)),
    ApartamentoData(3, "Botafogo 506", date(2026, 2, 1)),
]

# Metadados extras para o seed do banco (quartos/capacidade/endereço).
APARTAMENTOS_META: dict[int, dict] = {
    1: {"endereco": "Av. Atlântica, 302 - Copacabana", "quartos": 1, "capacidade": 3},
    2: {"endereco": "Rua Visconde de Pirajá, 1104 - Ipanema", "quartos": 2, "capacidade": 4},
    3: {"endereco": "Rua Voluntários da Pátria, 506 - Botafogo", "quartos": 1, "capacidade": 2},
}


def _r(
    apto: int,
    ci: tuple[int, int],
    co: tuple[int, int],
    hosp: int,
    valor: str,
    limpeza: str,
    comissao: str,
) -> ReservaData:
    return ReservaData(
        apartamento_id=apto,
        check_in=date(2026, ci[0], ci[1]),
        check_out=date(2026, co[0], co[1]),
        num_hospedes=hosp,
        valor_hospedagem=D(valor),
        taxa_limpeza=D(limpeza),
        comissao=D(comissao),
    )


# --------------------------------------------------------------------------- #
# Reservas (canal omitido aqui; o seed do banco preenche; não afeta cálculo) #
# --------------------------------------------------------------------------- #
RESERVAS: list[ReservaData] = [
    _r(1, (1, 3), (1, 7), 2, "1200", "150", "48"),
    _r(1, (1, 12), (1, 15), 3, "900", "150", "36"),
    _r(2, (1, 5), (1, 12), 4, "2800", "250", "112"),
    _r(2, (1, 18), (1, 21), 2, "1200", "250", "48"),
    _r(1, (1, 25), (1, 30), 2, "1500", "150", "60"),
    _r(1, (2, 2), (2, 6), 2, "1200", "150", "48"),
    _r(2, (2, 10), (2, 17), 4, "2800", "250", "112"),
    _r(3, (2, 5), (2, 8), 2, "600", "100", "24"),
    _r(1, (2, 15), (2, 20), 3, "1500", "150", "60"),
    _r(2, (2, 22), (2, 28), 3, "2400", "250", "96"),
    _r(3, (2, 20), (2, 23), 2, "600", "100", "24"),
    _r(1, (3, 8), (3, 12), 2, "1200", "150", "48"),
    _r(2, (3, 15), (3, 22), 4, "2800", "250", "112"),
    _r(3, (3, 14), (3, 18), 2, "800", "100", "32"),
    _r(3, (3, 25), (3, 29), 2, "800", "100", "32"),
]

# Canal por índice (para o seed do banco).
RESERVAS_CANAL: list[str] = [
    "Airbnb", "Airbnb", "Airbnb", "Direto", "Airbnb",
    "Airbnb", "Airbnb", "Airbnb", "Booking", "Airbnb",
    "Booking", "Airbnb", "Airbnb", "Airbnb", "Direto",
]


def _d(
    apto: int | None,
    data: tuple[int, int],
    categoria: CategoriaDespesa,
    valor: str,
    dedutivel: bool,
) -> DespesaData:
    return DespesaData(
        apartamento_id=apto,
        data=date(2026, data[0], data[1]),
        categoria=categoria,
        valor=D(valor),
        dedutivel_ir=dedutivel,
    )


C = CategoriaDespesa
DESPESAS: list[DespesaData] = [
    _d(1, (1, 31), C.CONDOMINIO, "650", True),
    _d(1, (1, 31), C.LUZ, "180", False),
    _d(1, (1, 31), C.LIMPEZA, "450", False),
    _d(2, (1, 31), C.CONDOMINIO, "1200", True),
    _d(2, (1, 31), C.LUZ, "220", False),
    _d(2, (1, 31), C.GAS, "90", False),
    _d(2, (1, 31), C.LIMPEZA, "500", False),
    _d(None, (1, 15), C.INTERNET, "120", False),
    _d(1, (2, 28), C.CONDOMINIO, "650", True),
    _d(1, (2, 28), C.LUZ, "195", False),
    _d(1, (2, 28), C.LIMPEZA, "300", False),
    _d(2, (2, 28), C.CONDOMINIO, "1200", True),
    _d(2, (2, 28), C.REPAROS, "380", True),
    _d(3, (2, 28), C.CONDOMINIO, "500", True),
    _d(3, (2, 28), C.LUZ, "140", False),
    _d(None, (2, 15), C.INTERNET, "120", False),
    _d(1, (3, 31), C.IPTU, "95", True),
    _d(2, (3, 31), C.CONDOMINIO, "1200", True),
    _d(3, (3, 31), C.LIMPEZA, "200", False),
    _d(None, (3, 15), C.INTERNET, "120", False),
]


# --------------------------------------------------------------------------- #
# Parâmetros de IR 2026 (tabela progressiva mensal)                           #
# --------------------------------------------------------------------------- #
def parametros_ir_2026() -> ParametrosIR:
    """Parâmetros tributários seedados para 2026.

    ``aplicar_redutor_transicao=False`` reproduz a planilha validada: isento
    até R$ 5.000 e imposto cheio acima disso (sem redução parcial na faixa de
    transição). Ver discrepância documentada no README.
    """
    return ParametrosIR(
        ano_vigencia=2026,
        faixas=[
            FaixaIR(D("0.00"), D("0.000"), D("0.00")),
            FaixaIR(D("2259.21"), D("0.075"), D("169.44")),
            FaixaIR(D("2826.66"), D("0.150"), D("381.44")),
            FaixaIR(D("3751.06"), D("0.225"), D("662.77")),
            FaixaIR(D("4664.69"), D("0.275"), D("896.00")),
        ],
        isencao_efetiva=D("5000.00"),
        transicao_inicio=D("5000.01"),
        transicao_fim=D("7350.00"),
        aplicar_redutor_transicao=False,
    )
