// Formatação pt-BR: moeda R$, datas dd/mm/yyyy, percentuais.

const moedaFmt = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

const numFmt = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function moeda(v: number | string | null | undefined): string {
  const n = typeof v === "string" ? Number(v) : v ?? 0;
  return moedaFmt.format(n || 0);
}

export function numero(v: number | null | undefined, casas = 1): string {
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  }).format(v ?? 0);
}

export function num2(v: number | null | undefined): string {
  return numFmt.format(v ?? 0);
}

/** Fração (0.2556) -> "25,6%". */
export function percent(fracao: number | null | undefined, casas = 1): string {
  return `${numero((fracao ?? 0) * 100, casas)}%`;
}

/** ISO "2026-01-03" -> "03/01/2026". */
export function dataBR(iso: string | null | undefined): string {
  if (!iso) return "";
  const [y, m, d] = iso.slice(0, 10).split("-");
  if (!y || !m || !d) return iso;
  return `${d}/${m}/${y}`;
}

export function hoje(): string {
  return new Date().toISOString().slice(0, 10);
}

const MESES = [
  "Jan",
  "Fev",
  "Mar",
  "Abr",
  "Mai",
  "Jun",
  "Jul",
  "Ago",
  "Set",
  "Out",
  "Nov",
  "Dez",
];

export function nomeMes(mes: number): string {
  return MESES[mes - 1] ?? String(mes);
}
