import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { GradeImposto } from "../api/types";
import { moeda, nomeMes, percent } from "../utils/format";

export default function Imposto() {
  const anoAtual = new Date().getFullYear();
  const [ano, setAno] = useState(2026);
  const [grade, setGrade] = useState<GradeImposto | null>(null);
  const [outras, setOutras] = useState<Record<number, string>>({});
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  const carregar = useCallback(
    (recalcular = false) => {
      setErro(null);
      setCarregando(true);
      const outrasNum: Record<number, number> = {};
      for (const [m, v] of Object.entries(outras)) {
        const n = Number(v);
        if (n) outrasNum[Number(m)] = n;
      }
      const req = recalcular
        ? api<GradeImposto>("/imposto/calcular", {
            method: "POST",
            body: { ano, outras_rendas: outrasNum },
          })
        : api<GradeImposto>("/imposto", { params: { ano } });
      req
        .then(setGrade)
        .catch((e) => setErro(e.message))
        .finally(() => setCarregando(false));
    },
    [ano, outras],
  );

  // Recarrega ao trocar de ano (sem recalcular outras rendas).
  useEffect(() => {
    setErro(null);
    setCarregando(true);
    api<GradeImposto>("/imposto", { params: { ano } })
      .then(setGrade)
      .catch((e) => setErro(e.message))
      .finally(() => setCarregando(false));
  }, [ano]);

  const anos = [anoAtual + 1, anoAtual, anoAtual - 1, 2026].filter(
    (v, i, a) => a.indexOf(v) === i,
  );

  return (
    <div>
      <div className="page-head">
        <h2>Imposto de Renda — Carnê-Leão</h2>
        <div className="head-acoes">
          <label className="inline">
            Ano
            <select value={ano} onChange={(e) => setAno(Number(e.target.value))}>
              {anos.map((a) => (
                <option key={a}>{a}</option>
              ))}
            </select>
          </label>
          <a
            className="btn btn-sec"
            href={`/api/exportar/imposto?formato=xlsx&ano=${ano}`}
            title="Disponível na Fase 4"
            onClick={(e) => {
              e.preventDefault();
              alert("Exportação chega na Fase 4.");
            }}
          >
            Exportar
          </a>
        </div>
      </div>

      <div className="disclaimer">
        ⚠️ {grade?.disclaimer ?? "Estimativa, não é orientação contábil."}
      </div>

      {erro && <div className="erro">{erro}</div>}
      {carregando && <div className="info">Calculando…</div>}

      {grade && (
        <>
          <table className="tabela">
            <thead>
              <tr>
                <th>Mês</th>
                <th className="num">Receita tributável</th>
                <th className="num">Despesas dedutíveis</th>
                <th className="num">Outras rendas</th>
                <th className="num">Base</th>
                <th className="num">Alíquota</th>
                <th className="num">Parcela deduzir</th>
                <th className="num">Imposto bruto</th>
                <th>Isento</th>
                <th className="num">Imposto devido</th>
              </tr>
            </thead>
            <tbody>
              {grade.linhas.map((l) => (
                <tr key={l.mes} className={l.isento ? "linha-isenta" : ""}>
                  <td>{nomeMes(l.mes)}</td>
                  <td className="num">{moeda(l.receita_tributavel)}</td>
                  <td className="num">{moeda(l.despesas_dedutiveis)}</td>
                  <td className="num">
                    <input
                      className="input-mini"
                      type="number"
                      step="0.01"
                      min={0}
                      value={outras[l.mes] ?? ""}
                      placeholder="0,00"
                      onChange={(e) =>
                        setOutras((o) => ({ ...o, [l.mes]: e.target.value }))
                      }
                    />
                  </td>
                  <td className="num">{moeda(l.base)}</td>
                  <td className="num">{percent(l.aliquota, 1)}</td>
                  <td className="num">{moeda(l.parcela_deduzir)}</td>
                  <td className="num">{moeda(l.imposto_bruto)}</td>
                  <td>{l.isento ? "Sim" : "—"}</td>
                  <td className="num">
                    <strong>{moeda(l.imposto_devido)}</strong>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={9} className="num">
                  <strong>Total devido no ano</strong>
                </td>
                <td className="num">
                  <strong>{moeda(grade.total_devido)}</strong>
                </td>
              </tr>
            </tfoot>
          </table>

          <div className="form-acoes esquerda">
            <button className="btn btn-primario" onClick={() => carregar(true)}>
              Recalcular com outras rendas
            </button>
            <small className="ajuda">
              Outras rendas do contribuinte (salário, outros aluguéis…) elevam a
              alíquota — a Receita soma todas as fontes no mês.
            </small>
          </div>
        </>
      )}
    </div>
  );
}
