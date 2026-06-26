import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { FaixaIR, ParametrosIR } from "../api/types";

export default function ParametrosIRPage() {
  const [params, setParams] = useState<ParametrosIR | null>(null);
  const [faixas, setFaixas] = useState<FaixaIR[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  function carregar() {
    setErro(null);
    api<ParametrosIR>("/parametros-ir")
      .then((p) => {
        setParams(p);
        setFaixas(p.faixas.map((f) => ({ ...f })));
      })
      .catch((e) => setErro(e.message));
  }

  useEffect(carregar, []);

  function setParam<K extends keyof ParametrosIR>(k: K, v: ParametrosIR[K]) {
    setParams((p) => (p ? { ...p, [k]: v } : p));
  }

  function setFaixa(i: number, campo: keyof FaixaIR, v: string) {
    setFaixas((fs) => fs.map((f, idx) => (idx === i ? { ...f, [campo]: v } : f)));
  }

  function addFaixa() {
    setFaixas((fs) => [
      ...fs,
      { limite_inferior: "0", aliquota: "0", parcela_deduzir: "0" },
    ]);
  }

  function removeFaixa(i: number) {
    setFaixas((fs) => fs.filter((_, idx) => idx !== i));
  }

  async function salvar(e: FormEvent) {
    e.preventDefault();
    if (!params) return;
    setErro(null);
    setOk(null);
    try {
      const body = {
        isencao_efetiva: params.isencao_efetiva,
        transicao_inicio: params.transicao_inicio,
        transicao_fim: params.transicao_fim,
        aplicar_redutor_transicao: params.aplicar_redutor_transicao,
        faixas: faixas.map((f) => ({
          limite_inferior: f.limite_inferior,
          aliquota: f.aliquota,
          parcela_deduzir: f.parcela_deduzir,
        })),
      };
      const atualizado = await api<ParametrosIR>("/parametros-ir", {
        method: "PUT",
        body,
      });
      setParams(atualizado);
      setFaixas(atualizado.faixas.map((f) => ({ ...f })));
      setOk("Parâmetros salvos.");
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Erro ao salvar");
    }
  }

  if (!params) {
    return (
      <div>
        <h2>Parâmetros de IR</h2>
        {erro && <div className="erro">{erro}</div>}
      </div>
    );
  }

  return (
    <div>
      <div className="page-head">
        <h2>Parâmetros de IR ({params.ano_vigencia})</h2>
      </div>

      <div className="disclaimer">
        Alterações aqui mudam apenas o banco de dados (a legislação muda). A
        alíquota é uma fração (ex.: <code>0.275</code> = 27,5%).
      </div>

      <form className="form" onSubmit={salvar}>
        <div className="form-row">
          <label>
            Isenção efetiva (R$)
            <input
              type="number"
              step="0.01"
              value={params.isencao_efetiva}
              onChange={(e) => setParam("isencao_efetiva", e.target.value)}
            />
          </label>
          <label>
            Transição início (R$)
            <input
              type="number"
              step="0.01"
              value={params.transicao_inicio}
              onChange={(e) => setParam("transicao_inicio", e.target.value)}
            />
          </label>
          <label>
            Transição fim (R$)
            <input
              type="number"
              step="0.01"
              value={params.transicao_fim}
              onChange={(e) => setParam("transicao_fim", e.target.value)}
            />
          </label>
        </div>

        <label className="check">
          <input
            type="checkbox"
            checked={params.aplicar_redutor_transicao}
            onChange={(e) =>
              setParam("aplicar_redutor_transicao", e.target.checked)
            }
          />
          Aplicar redutor na faixa de transição (interpolação linear — confirmar
          fórmula 2026 com contador)
        </label>

        <h3>Faixas progressivas mensais</h3>
        <table className="tabela">
          <thead>
            <tr>
              <th className="num">Limite inferior (R$)</th>
              <th className="num">Alíquota (fração)</th>
              <th className="num">Parcela a deduzir (R$)</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {faixas.map((f, i) => (
              <tr key={i}>
                <td className="num">
                  <input
                    type="number"
                    step="0.01"
                    value={f.limite_inferior}
                    onChange={(e) => setFaixa(i, "limite_inferior", e.target.value)}
                  />
                </td>
                <td className="num">
                  <input
                    type="number"
                    step="0.0001"
                    value={f.aliquota}
                    onChange={(e) => setFaixa(i, "aliquota", e.target.value)}
                  />
                </td>
                <td className="num">
                  <input
                    type="number"
                    step="0.01"
                    value={f.parcela_deduzir}
                    onChange={(e) => setFaixa(i, "parcela_deduzir", e.target.value)}
                  />
                </td>
                <td>
                  <button
                    type="button"
                    className="btn-link perigo"
                    onClick={() => removeFaixa(i)}
                  >
                    Remover
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <button type="button" className="btn btn-sec" onClick={addFaixa}>
          + Adicionar faixa
        </button>

        {erro && <div className="erro">{erro}</div>}
        {ok && <div className="info sucesso">{ok}</div>}

        <div className="form-acoes esquerda">
          <button type="submit" className="btn btn-primario">
            Salvar parâmetros
          </button>
        </div>
      </form>
    </div>
  );
}
