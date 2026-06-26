"""Testes da lógica pura de importação de CSV."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.enums import StatusReserva
from app.services import importacao as imp

D = Decimal


def test_parse_data_formatos():
    assert imp.parse_data("2026-01-03") == date(2026, 1, 3)
    assert imp.parse_data("03/01/2026") == date(2026, 1, 3)  # DD/MM/YYYY preferido
    assert imp.parse_data("") is None
    assert imp.parse_data("xx") is None


def test_parse_dinheiro_br_us():
    assert imp.parse_dinheiro("1.200,00") == D("1200.00")  # BR
    assert imp.parse_dinheiro("1,200.00") == D("1200.00")  # US
    assert imp.parse_dinheiro("R$ 900,50") == D("900.50")
    assert imp.parse_dinheiro("$1,500") == D("1500")
    assert imp.parse_dinheiro("48") == D("48")
    assert imp.parse_dinheiro("") == D("0")
    assert imp.parse_dinheiro("abc") is None


def test_parse_status():
    assert imp.parse_status("Cancelled") == StatusReserva.CANCELADA
    assert imp.parse_status("Past guest") == StatusReserva.CONCLUIDA
    assert imp.parse_status("Confirmed") == StatusReserva.CONFIRMADA
    assert imp.parse_status("") == StatusReserva.CONFIRMADA


def test_ler_csv_virgula_e_ponto_e_virgula():
    csv_v = "a,b\n1,2\n"
    cols, linhas = imp.ler_csv(csv_v)
    assert cols == ["a", "b"]
    assert linhas == [{"a": "1", "b": "2"}]

    csv_pv = "a;b\n1;2\n"
    cols2, linhas2 = imp.ler_csv(csv_pv)
    assert cols2 == ["a", "b"]
    assert linhas2 == [{"a": "1", "b": "2"}]


def test_sugerir_mapeamento_airbnb_en():
    colunas = [
        "Confirmation code", "Status", "Guest name", "# of guests",
        "Start date", "End date", "Listing", "Earnings",
    ]
    s = imp.sugerir_mapeamento(colunas)
    assert s["codigo_confirmacao"] == "Confirmation code"
    assert s["check_in"] == "Start date"
    assert s["check_out"] == "End date"
    assert s["num_hospedes"] == "# of guests"
    assert s["listing"] == "Listing"
    assert s["valor_hospedagem"] == "Earnings"


def test_sugerir_mapeamento_airbnb_pt():
    colunas = [
        "Código de confirmação", "Data de início", "Data de término",
        "Anúncio", "Nº de hóspedes", "Ganhos",
    ]
    s = imp.sugerir_mapeamento(colunas)
    assert s["codigo_confirmacao"] == "Código de confirmação"
    assert s["check_in"] == "Data de início"
    assert s["check_out"] == "Data de término"
    assert s["listing"] == "Anúncio"
    assert s["valor_hospedagem"] == "Ganhos"


def _linhas_exemplo():
    return [
        {
            "cod": "HMABC1", "anuncio": "Copa 302", "ini": "03/01/2026",
            "fim": "07/01/2026", "hosp": "2", "valor": "1.200,00",
        },
        {  # duplicada (mesmo código) -> ignorar
            "cod": "HMABC1", "anuncio": "Copa 302", "ini": "10/01/2026",
            "fim": "12/01/2026", "hosp": "2", "valor": "600,00",
        },
        {  # listing não mapeado -> erro
            "cod": "HMXYZ2", "anuncio": "Desconhecido", "ini": "05/01/2026",
            "fim": "08/01/2026", "hosp": "3", "valor": "900,00",
        },
        {  # data inválida -> erro
            "cod": "HMERR3", "anuncio": "Copa 302", "ini": "31/02/2026",
            "fim": "08/01/2026", "hosp": "2", "valor": "900,00",
        },
    ]


_MAPA = {
    "codigo_confirmacao": "cod",
    "listing": "anuncio",
    "check_in": "ini",
    "check_out": "fim",
    "num_hospedes": "hosp",
    "valor_hospedagem": "valor",
}


def test_processar_dedup_erros_criar():
    previa = imp.processar(
        _linhas_exemplo(), _MAPA, {"Copa 302": 1}, codigos_existentes=set()
    )
    assert previa.total == 4
    assert previa.criar == 1
    assert previa.ignorar == 1  # código duplicado no arquivo
    assert previa.erro == 2  # listing não mapeado + data inválida

    criada = next(l for l in previa.linhas if l.acao == "criar")
    assert criada.apartamento_id == 1
    assert criada.check_in == date(2026, 1, 3)
    assert criada.valor_hospedagem == D("1200.00")
    assert criada.num_hospedes == 2


def test_processar_dedup_contra_banco():
    previa = imp.processar(
        _linhas_exemplo()[:1], _MAPA, {"Copa 302": 1},
        codigos_existentes={"HMABC1"},
    )
    assert previa.criar == 0
    assert previa.ignorar == 1
