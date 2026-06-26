"""Fixtures de teste baseadas no dataset canônico (seção 11)."""
from __future__ import annotations

import os
import sys
from datetime import date

import pytest

# Garante que ``app`` seja importável ao rodar pytest a partir de backend/.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.seed_data import (  # noqa: E402
    APARTAMENTOS,
    DESPESAS,
    RESERVAS,
    parametros_ir_2026,
)


@pytest.fixture
def apartamentos():
    return list(APARTAMENTOS)


@pytest.fixture
def reservas():
    return list(RESERVAS)


@pytest.fixture
def despesas():
    return list(DESPESAS)


@pytest.fixture
def params_ir():
    return parametros_ir_2026()


@pytest.fixture
def periodo_q1():
    """01/01/2026 a 31/03/2026 (período dos critérios de aceite)."""
    return date(2026, 1, 1), date(2026, 3, 31)
