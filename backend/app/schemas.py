"""Schemas Pydantic v2 de entrada/saída da API.

Convenção: valores monetários de ENTRADA são ``Decimal`` (preservam precisão
até o banco). Valores de SAÍDA já calculados são serializados como ``float``
arredondado (borda de apresentação) para consumo direto por gráficos.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.enums import Canal, CategoriaDespesa, StatusReserva

# Decimal monetário >= 0, NUMERIC(12,2).
Dinheiro = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]


def _q2(v: Decimal) -> float:
    return float(v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _q4(v: Decimal) -> float:
    return float(v.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


# --------------------------------------------------------------------------- #
# Auth                                                                         #
# --------------------------------------------------------------------------- #
class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    ativo: bool


# --------------------------------------------------------------------------- #
# Apartamentos                                                                 #
# --------------------------------------------------------------------------- #
class ApartamentoBase(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    endereco: str | None = Field(default=None, max_length=255)
    quartos: int = Field(ge=0)
    capacidade: int = Field(ge=1)
    data_inicio_operacao: date
    ativo: bool = True


class ApartamentoCreate(ApartamentoBase):
    pass


class ApartamentoUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    endereco: str | None = Field(default=None, max_length=255)
    quartos: int | None = Field(default=None, ge=0)
    capacidade: int | None = Field(default=None, ge=1)
    data_inicio_operacao: date | None = None
    ativo: bool | None = None


class ApartamentoOut(ApartamentoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# --------------------------------------------------------------------------- #
# Reservas                                                                     #
# --------------------------------------------------------------------------- #
class ReservaBase(BaseModel):
    apartamento_id: int
    check_in: date
    check_out: date
    num_hospedes: int = Field(ge=1)
    valor_hospedagem: Dinheiro
    taxa_limpeza: Dinheiro = Decimal("0")
    comissao: Dinheiro = Decimal("0")
    canal: Canal = Canal.AIRBNB
    status: StatusReserva = StatusReserva.CONFIRMADA
    codigo_confirmacao: str | None = Field(default=None, max_length=64)
    observacao: str | None = None

    @model_validator(mode="after")
    def _checa_datas(self) -> "ReservaBase":
        if self.check_out <= self.check_in:
            raise ValueError("check_out deve ser posterior a check_in")
        return self


class ReservaCreate(ReservaBase):
    pass


class ReservaUpdate(BaseModel):
    apartamento_id: int | None = None
    check_in: date | None = None
    check_out: date | None = None
    num_hospedes: int | None = Field(default=None, ge=1)
    valor_hospedagem: Dinheiro | None = None
    taxa_limpeza: Dinheiro | None = None
    comissao: Dinheiro | None = None
    canal: Canal | None = None
    status: StatusReserva | None = None
    codigo_confirmacao: str | None = Field(default=None, max_length=64)
    observacao: str | None = None


class ReservaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    apartamento_id: int
    check_in: date
    check_out: date
    num_hospedes: int
    valor_hospedagem: Decimal
    taxa_limpeza: Decimal
    comissao: Decimal
    canal: Canal
    status: StatusReserva
    codigo_confirmacao: str | None = None
    observacao: str | None = None
    created_at: datetime | None = None
    # Derivados
    noites: int = 0
    receita_liquida: Decimal = Decimal("0")

    @model_validator(mode="after")
    def _derivados(self) -> "ReservaOut":
        object.__setattr__(self, "noites", (self.check_out - self.check_in).days)
        object.__setattr__(
            self,
            "receita_liquida",
            self.valor_hospedagem + self.taxa_limpeza - self.comissao,
        )
        return self


class ReservaResult(BaseModel):
    """Resposta de criação/edição: a reserva + avisos não bloqueantes."""

    reserva: ReservaOut
    avisos: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Despesas                                                                     #
# --------------------------------------------------------------------------- #
class DespesaBase(BaseModel):
    apartamento_id: int | None = None  # None = despesa comum
    data: date
    categoria: CategoriaDespesa
    valor: Dinheiro
    dedutivel_ir: bool = False
    recorrente: bool = False
    observacao: str | None = None


class DespesaCreate(DespesaBase):
    pass


class DespesaUpdate(BaseModel):
    apartamento_id: int | None = None
    data: date | None = None
    categoria: CategoriaDespesa | None = None
    valor: Dinheiro | None = None
    dedutivel_ir: bool | None = None
    recorrente: bool | None = None
    observacao: str | None = None


class DespesaOut(DespesaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# --------------------------------------------------------------------------- #
# Métricas                                                                     #
# --------------------------------------------------------------------------- #
class MetricasOut(BaseModel):
    inicio: date
    fim: date
    dias_no_periodo: int
    num_apartamentos: int
    num_reservas: int
    noites_reservadas: int
    total_hospedes: int
    media_hospedes_por_reserva: float
    los_medio: float
    receita_diarias: float
    receita_liquida_recebida: float
    adr: float
    noites_disponiveis: int
    ocupacao: float
    vacancia: float
    revpar: float
    despesas_totais: float
    despesas_por_categoria: dict[str, float]
    imposto_estimado: float
    lucro_liquido: float

    @classmethod
    def from_dataclass(cls, m) -> "MetricasOut":
        return cls(
            inicio=m.inicio,
            fim=m.fim,
            dias_no_periodo=m.dias_no_periodo,
            num_apartamentos=m.num_apartamentos,
            num_reservas=m.num_reservas,
            noites_reservadas=m.noites_reservadas,
            total_hospedes=m.total_hospedes,
            media_hospedes_por_reserva=_q2(m.media_hospedes_por_reserva),
            los_medio=_q2(m.los_medio),
            receita_diarias=_q2(m.receita_diarias),
            receita_liquida_recebida=_q2(m.receita_liquida_recebida),
            adr=_q2(m.adr),
            noites_disponiveis=m.noites_disponiveis,
            ocupacao=_q4(m.ocupacao),
            vacancia=_q4(m.vacancia),
            revpar=_q2(m.revpar),
            despesas_totais=_q2(m.despesas_totais),
            despesas_por_categoria={
                k: _q2(v) for k, v in m.despesas_por_categoria.items()
            },
            imposto_estimado=_q2(m.imposto_estimado),
            lucro_liquido=_q2(m.lucro_liquido),
        )


class MetricaMensalOut(BaseModel):
    """Um mês da série temporal (para gráficos receita × despesas)."""

    ano: int
    mes: int
    rotulo: str  # ex.: "01/2026"
    noites_reservadas: int
    receita_diarias: float
    receita_liquida_recebida: float
    despesas_totais: float
    imposto_estimado: float
    ocupacao: float


class MetricasApartamentoOut(BaseModel):
    apartamento_id: int
    nome: str
    noites: int
    noites_disponiveis: int
    ocupacao: float
    vacancia: float
    hospedes: int
    receita_diarias: float
    adr: float
    despesas: float

    @classmethod
    def from_dataclass(cls, m) -> "MetricasApartamentoOut":
        return cls(
            apartamento_id=m.apartamento_id,
            nome=m.nome,
            noites=m.noites,
            noites_disponiveis=m.noites_disponiveis,
            ocupacao=_q4(m.ocupacao),
            vacancia=_q4(m.vacancia),
            hospedes=m.hospedes,
            receita_diarias=_q2(m.receita_diarias),
            adr=_q2(m.adr),
            despesas=_q2(m.despesas),
        )


# --------------------------------------------------------------------------- #
# Imposto                                                                      #
# --------------------------------------------------------------------------- #
class LinhaImpostoOut(BaseModel):
    ano: int
    mes: int
    receita_tributavel: float
    despesas_dedutiveis: float
    outras_rendas: float
    base: float
    aliquota: float
    parcela_deduzir: float
    imposto_bruto: float
    isento: bool
    imposto_devido: float

    @classmethod
    def from_dataclass(cls, l) -> "LinhaImpostoOut":
        return cls(
            ano=l.ano,
            mes=l.mes,
            receita_tributavel=_q2(l.receita_tributavel),
            despesas_dedutiveis=_q2(l.despesas_dedutiveis),
            outras_rendas=_q2(l.outras_rendas),
            base=_q2(l.base),
            aliquota=_q4(l.aliquota),
            parcela_deduzir=_q2(l.parcela_deduzir),
            imposto_bruto=_q2(l.imposto_bruto),
            isento=l.isento,
            imposto_devido=_q2(l.imposto_devido),
        )


class ImpostoCalcularRequest(BaseModel):
    """Recalcula a grade com 'outras rendas' por mês (1..12)."""

    ano: int
    outras_rendas: dict[int, Decimal] = Field(default_factory=dict)


class GradeImpostoOut(BaseModel):
    ano: int
    linhas: list[LinhaImpostoOut]
    total_devido: float
    disclaimer: str = (
        "Estimativa, não é orientação contábil. "
        "Confirme alíquotas e deduções com seu contador."
    )

    @classmethod
    def from_dataclass(cls, g) -> "GradeImpostoOut":
        return cls(
            ano=g.ano,
            linhas=[LinhaImpostoOut.from_dataclass(x) for x in g.linhas],
            total_devido=_q2(g.total_devido),
        )


# --------------------------------------------------------------------------- #
# Parâmetros de IR                                                             #
# --------------------------------------------------------------------------- #
class FaixaIRIn(BaseModel):
    limite_inferior: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    aliquota: Decimal = Field(ge=0, le=1, max_digits=6, decimal_places=4)
    parcela_deduzir: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class FaixaIROut(FaixaIRIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ParametrosIROut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ano_vigencia: int
    isencao_efetiva: Decimal
    transicao_inicio: Decimal
    transicao_fim: Decimal
    aplicar_redutor_transicao: bool
    faixas: list[FaixaIROut]


class ParametrosIRUpdate(BaseModel):
    isencao_efetiva: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )
    transicao_inicio: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )
    transicao_fim: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )
    aplicar_redutor_transicao: bool | None = None
    faixas: list[FaixaIRIn] | None = None
