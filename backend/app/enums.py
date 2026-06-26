"""Enumerações de domínio (pt-BR)."""
from __future__ import annotations

import enum


class Canal(str, enum.Enum):
    """Canal de origem da reserva."""

    AIRBNB = "Airbnb"
    BOOKING = "Booking"
    DIRETO = "Direto"


class StatusReserva(str, enum.Enum):
    """Situação da reserva."""

    CONFIRMADA = "Confirmada"
    CONCLUIDA = "Concluída"
    CANCELADA = "Cancelada"


class CategoriaDespesa(str, enum.Enum):
    """Categoria de despesa operacional."""

    LIMPEZA = "Limpeza"
    LUZ = "Luz"
    CONDOMINIO = "Condomínio"
    GAS = "Gás"
    REPAROS = "Reparos"
    IPTU = "IPTU"
    INTERNET = "Internet"
    SEGURO = "Seguro"
    OUTROS = "Outros"
