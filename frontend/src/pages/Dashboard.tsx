import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import { useApartamentos } from "../components/useApartamentos";
import type {
  MetricaMensal,
  Metricas,
  MetricasApartamento,
} from "../api/types";
import { moeda, num2, numero, percent } from "../utils/format";

type Atalho = "mes" | "ano" | "90dias";

function intervaloAtalho(a: Atalho): { inicio: string; fim: string } {
  const hoje = new Date();
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  if (a === "mes") {
    const ini = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
    const fim = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0);
    return { inicio: iso(ini), fim: iso(fim) };
  }
  if (a === "ano") {
    return {
      inicio: `${hoje.getFullYear()}-01-01`,
      fim: `${hoje.getFullYear()}-12-31`,
    };
  }
  const ini = new Date(hoje);
  ini.setDate(ini.getDate() - 89);
  return { inicio: iso(ini), fim: iso(hoje) };
}

const CORES = [
  "#2563eb",
  "#16a34a",
  "#f59e0b",
  "#dc2626",
  "#7c3aed",
  "#0891b2",
  "#db2777",
  "#65a30d",
  "#9333ea",
];

function Kpi({
  titulo,
  valor,
  sub,
}: {
  titulo: string;
  valor: string;
  sub?: string;
}) {
  return (
    <div className="kpi">
      <div className="kpi-titulo">{titulo}</div>
      <div className="kpi-valor">{valor}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  );
}

export default function Dashboard() {
  const { apartamentos } = useApartamentos(true);
  // Padrão: ano corrente (cobre o dataset de exemplo de 2026).
  const padrao = intervaloAtalho("ano");
  const [inicio, setInicio] = useState(padrao.inicio);
  const [fim, setFim] = useState(padrao.fim);
  const [apartamentoId, setApartamentoId] = useState<number | "">("");

  const [metricas, setMetricas] = useState<Metricas | null>(null);
  const [porApto, setPorApto] = useState<MetricasApartamento[]>([]);
  const [mensal, setMensal] = useState<MetricaMensal[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  useEffect(() => {
    let vivo = true;
    setCarregando(true);
    setErro(null);
    const params = {
      inicio,
      fim,
      apartamento_id: apartamentoId === "" ? undefined : apartamentoId,
    };
    Promise.all([
      api<Metricas>("/metricas", { params }),
      api<MetricasApartamento[]>("/metricas/por-apartamento", {
        params: { inicio, fim },
      }),
      api<MetricaMensal[]>("/metricas/mensal", { params }),
    ])
      .then(([m, pa, ms]) => {
        if (!vivo) return;
        setMetricas(m);
        setPorApto(pa);
        setMensal(ms);
      })
      .catch((e) => vivo && setErro(e.message))
      .finally(() => vivo && setCarregando(false));
    return () => {
      vivo = false;
    };
  }, [inicio, fim, apartamentoId]);

  const dadosCategoria = useMemo(() => {
    if (!metricas) return [];
    return Object.entries(metricas.despesas_por_categoria)
      .map(([nome, valor]) => ({ nome, valor }))
      .sort((a, b) => b.valor - a.valor);
  }, [metricas]);

  const dadosOcupacao = porApto.map((p) => ({
    nome: p.nome,
    ocupacao: +(p.ocupacao * 100).toFixed(1),
  }));

  return (
    <div>
      <div className="page-head">
        <h2>Dashboard</h2>
      </div>

      <div className="filtros">
        <label>
          Apartamento
          <select
            value={apartamentoId}
            onChange={(e) =>
              setApartamentoId(e.target.value === "" ? "" : Number(e.target.value))
            }
          >
            <option value="">Todos</option>
            {apartamentos.map((a) => (
              <option key={a.id} value={a.id}>
                {a.nome}
              </option>
            ))}
          </select>
        </label>
        <label>
          Início
          <input
            type="date"
            value={inicio}
            onChange={(e) => setInicio(e.target.value)}
          />
        </label>
        <label>
          Fim
          <input type="date" value={fim} onChange={(e) => setFim(e.target.value)} />
        </label>
        <div className="atalhos">
          <button
            className="btn btn-sec"
            onClick={() => {
              const i = intervaloAtalho("mes");
              setInicio(i.inicio);
              setFim(i.fim);
            }}
          >
            Mês atual
          </button>
          <button
            className="btn btn-sec"
            onClick={() => {
              const i = intervaloAtalho("ano");
              setInicio(i.inicio);
              setFim(i.fim);
            }}
          >
            Ano
          </button>
          <button
            className="btn btn-sec"
            onClick={() => {
              const i = intervaloAtalho("90dias");
              setInicio(i.inicio);
              setFim(i.fim);
            }}
          >
            Últimos 90 dias
          </button>
        </div>
      </div>

      {erro && <div className="erro">{erro}</div>}
      {carregando && <div className="info">Carregando…</div>}

      {metricas && (
        <>
          <div className="kpis">
            <Kpi titulo="Receita de diárias" valor={moeda(metricas.receita_diarias)} />
            <Kpi
              titulo="Receita líquida"
              valor={moeda(metricas.receita_liquida_recebida)}
            />
            <Kpi titulo="Despesas" valor={moeda(metricas.despesas_totais)} />
            <Kpi titulo="Imposto estimado" valor={moeda(metricas.imposto_estimado)} />
            <Kpi
              titulo="Lucro líquido"
              valor={moeda(metricas.lucro_liquido)}
              sub={`${metricas.num_reservas} reservas`}
            />
            <Kpi titulo="Ocupação" valor={percent(metricas.ocupacao)} sub={`Vacância ${percent(metricas.vacancia)}`} />
            <Kpi titulo="ADR (diária média)" valor={moeda(metricas.adr)} />
            <Kpi titulo="RevPAR" valor={moeda(metricas.revpar)} />
            <Kpi
              titulo="Noites reservadas"
              valor={num2(metricas.noites_reservadas)}
              sub={`de ${metricas.noites_disponiveis} disponíveis`}
            />
            <Kpi
              titulo="Hóspedes"
              valor={String(metricas.total_hospedes)}
              sub={`média ${numero(metricas.media_hospedes_por_reserva)}/reserva`}
            />
            <Kpi titulo="LOS médio" valor={`${numero(metricas.los_medio)} noites`} />
            <Kpi titulo="Dias no período" valor={String(metricas.dias_no_periodo)} />
          </div>

          <div className="graficos">
            <div className="card">
              <h3>Ocupação por apartamento</h3>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={dadosOcupacao}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="nome" />
                  <YAxis unit="%" />
                  <Tooltip formatter={(v: number) => `${v}%`} />
                  <Bar dataKey="ocupacao" name="Ocupação" fill="#2563eb" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="card">
              <h3>Receita × Despesas por mês</h3>
              <ResponsiveContainer width="100%" height={260}>
                <ComposedChart data={mensal}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="rotulo" />
                  <YAxis />
                  <Tooltip formatter={(v: number) => moeda(v)} />
                  <Legend />
                  <Bar
                    dataKey="receita_diarias"
                    name="Receita"
                    fill="#16a34a"
                  />
                  <Bar
                    dataKey="despesas_totais"
                    name="Despesas"
                    fill="#dc2626"
                  />
                  <Line
                    type="monotone"
                    dataKey="imposto_estimado"
                    name="Imposto"
                    stroke="#f59e0b"
                    strokeWidth={2}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            <div className="card">
              <h3>Despesas por categoria</h3>
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={dadosCategoria}
                    dataKey="valor"
                    nameKey="nome"
                    cx="50%"
                    cy="50%"
                    outerRadius={90}
                    label={(e: { nome: string }) => e.nome}
                  >
                    {dadosCategoria.map((_, i) => (
                      <Cell key={i} fill={CORES[i % CORES.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => moeda(v)} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card">
            <h3>Resumo por apartamento</h3>
            <table className="tabela">
              <thead>
                <tr>
                  <th>Apartamento</th>
                  <th className="num">Noites</th>
                  <th className="num">Ocupação</th>
                  <th className="num">Vacância</th>
                  <th className="num">Hóspedes</th>
                  <th className="num">Receita diárias</th>
                  <th className="num">ADR</th>
                  <th className="num">Despesas</th>
                </tr>
              </thead>
              <tbody>
                {porApto.map((p) => (
                  <tr key={p.apartamento_id}>
                    <td>{p.nome}</td>
                    <td className="num">{p.noites}</td>
                    <td className="num">{percent(p.ocupacao)}</td>
                    <td className="num">{percent(p.vacancia)}</td>
                    <td className="num">{p.hospedes}</td>
                    <td className="num">{moeda(p.receita_diarias)}</td>
                    <td className="num">{moeda(p.adr)}</td>
                    <td className="num">{moeda(p.despesas)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
