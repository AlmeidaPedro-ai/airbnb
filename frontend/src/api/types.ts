// Tipos que espelham os schemas Pydantic do backend.

export type Canal = "Airbnb" | "Booking" | "Direto";
export type StatusReserva = "Confirmada" | "Concluída" | "Cancelada";
export type CategoriaDespesa =
  | "Limpeza"
  | "Luz"
  | "Condomínio"
  | "Gás"
  | "Reparos"
  | "IPTU"
  | "Internet"
  | "Seguro"
  | "Outros";

export const CANAIS: Canal[] = ["Airbnb", "Booking", "Direto"];
export const STATUS_RESERVA: StatusReserva[] = [
  "Confirmada",
  "Concluída",
  "Cancelada",
];
export const CATEGORIAS: CategoriaDespesa[] = [
  "Limpeza",
  "Luz",
  "Condomínio",
  "Gás",
  "Reparos",
  "IPTU",
  "Internet",
  "Seguro",
  "Outros",
];

export interface Apartamento {
  id: number;
  nome: string;
  endereco: string | null;
  quartos: number;
  capacidade: number;
  data_inicio_operacao: string; // ISO date
  ativo: boolean;
}

export type ApartamentoInput = Omit<Apartamento, "id">;

export interface Reserva {
  id: number;
  apartamento_id: number;
  check_in: string;
  check_out: string;
  num_hospedes: number;
  valor_hospedagem: string;
  taxa_limpeza: string;
  comissao: string;
  canal: Canal;
  status: StatusReserva;
  codigo_confirmacao: string | null;
  observacao: string | null;
  created_at: string | null;
  noites: number;
  receita_liquida: string;
}

export interface ReservaInput {
  apartamento_id: number;
  check_in: string;
  check_out: string;
  num_hospedes: number;
  valor_hospedagem: string;
  taxa_limpeza: string;
  comissao: string;
  canal: Canal;
  status: StatusReserva;
  codigo_confirmacao?: string | null;
  observacao?: string | null;
}

export interface ReservaResult {
  reserva: Reserva;
  avisos: string[];
}

export interface Despesa {
  id: number;
  apartamento_id: number | null;
  data: string;
  categoria: CategoriaDespesa;
  valor: string;
  dedutivel_ir: boolean;
  recorrente: boolean;
  observacao: string | null;
}

export type DespesaInput = Omit<Despesa, "id">;

export interface Metricas {
  inicio: string;
  fim: string;
  dias_no_periodo: number;
  num_apartamentos: number;
  num_reservas: number;
  noites_reservadas: number;
  total_hospedes: number;
  media_hospedes_por_reserva: number;
  los_medio: number;
  receita_diarias: number;
  receita_liquida_recebida: number;
  adr: number;
  noites_disponiveis: number;
  ocupacao: number;
  vacancia: number;
  revpar: number;
  despesas_totais: number;
  despesas_por_categoria: Record<string, number>;
  imposto_estimado: number;
  lucro_liquido: number;
}

export interface MetricasApartamento {
  apartamento_id: number;
  nome: string;
  noites: number;
  noites_disponiveis: number;
  ocupacao: number;
  vacancia: number;
  hospedes: number;
  receita_diarias: number;
  adr: number;
  despesas: number;
}

export interface MetricaMensal {
  ano: number;
  mes: number;
  rotulo: string;
  noites_reservadas: number;
  receita_diarias: number;
  receita_liquida_recebida: number;
  despesas_totais: number;
  imposto_estimado: number;
  ocupacao: number;
}

export interface LinhaImposto {
  ano: number;
  mes: number;
  receita_tributavel: number;
  despesas_dedutiveis: number;
  outras_rendas: number;
  base: number;
  aliquota: number;
  parcela_deduzir: number;
  imposto_bruto: number;
  isento: boolean;
  imposto_devido: number;
}

export interface GradeImposto {
  ano: number;
  linhas: LinhaImposto[];
  total_devido: number;
  disclaimer: string;
}

export interface FaixaIR {
  id?: number;
  limite_inferior: string;
  aliquota: string;
  parcela_deduzir: string;
}

export interface ParametrosIR {
  id: number;
  ano_vigencia: number;
  isencao_efetiva: string;
  transicao_inicio: string;
  transicao_fim: string;
  aplicar_redutor_transicao: boolean;
  faixas: FaixaIR[];
}
