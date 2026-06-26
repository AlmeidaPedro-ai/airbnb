import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, baixar } from "../api/client";
import Modal from "../components/Modal";
import { nomeApartamento, useApartamentos } from "../components/useApartamentos";
import {
  CATEGORIAS,
  type CategoriaDespesa,
  type Despesa,
  type DespesaInput,
} from "../api/types";
import { dataBR, hoje, moeda } from "../utils/format";

const VAZIO: DespesaInput = {
  apartamento_id: null,
  data: hoje(),
  categoria: "Condomínio",
  valor: "0",
  dedutivel_ir: false,
  recorrente: false,
  observacao: "",
};

export default function Despesas() {
  const { apartamentos } = useApartamentos();
  const [lista, setLista] = useState<Despesa[]>([]);
  const [fApto, setFApto] = useState<string>("");
  const [fCat, setFCat] = useState<CategoriaDespesa | "">("");
  const [fInicio, setFInicio] = useState("");
  const [fFim, setFFim] = useState("");
  const [erro, setErro] = useState<string | null>(null);

  const [modalAberto, setModalAberto] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<DespesaInput>(VAZIO);
  const [erroForm, setErroForm] = useState<string | null>(null);

  const carregar = useCallback(() => {
    setErro(null);
    api<Despesa[]>("/despesas", {
      params: {
        apartamento_id: fApto === "" || fApto === "comum" ? undefined : fApto,
        categoria: fCat || undefined,
        inicio: fInicio || undefined,
        fim: fFim || undefined,
        incluir_comuns: fApto === "comum" ? "false" : "true",
      },
    })
      .then((d) =>
        setLista(fApto === "comum" ? d.filter((x) => x.apartamento_id === null) : d),
      )
      .catch((e) => setErro(e.message));
  }, [fApto, fCat, fInicio, fFim]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  function abrirNova() {
    setEditId(null);
    setForm(VAZIO);
    setErroForm(null);
    setModalAberto(true);
  }

  function abrirEdicao(d: Despesa) {
    setEditId(d.id);
    setForm({
      apartamento_id: d.apartamento_id,
      data: d.data,
      categoria: d.categoria,
      valor: d.valor,
      dedutivel_ir: d.dedutivel_ir,
      recorrente: d.recorrente,
      observacao: d.observacao ?? "",
    });
    setErroForm(null);
    setModalAberto(true);
  }

  async function salvar(e: FormEvent) {
    e.preventDefault();
    setErroForm(null);
    try {
      if (editId) {
        await api(`/despesas/${editId}`, { method: "PUT", body: form });
      } else {
        await api("/despesas", { method: "POST", body: form });
      }
      setModalAberto(false);
      carregar();
    } catch (err) {
      setErroForm(err instanceof Error ? err.message : "Erro ao salvar");
    }
  }

  async function excluir(id: number) {
    if (!confirm("Excluir esta despesa?")) return;
    await api(`/despesas/${id}`, { method: "DELETE" });
    carregar();
  }

  function set<K extends keyof DespesaInput>(k: K, v: DespesaInput[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  const total = lista.reduce((s, d) => s + Number(d.valor), 0);

  return (
    <div>
      <div className="page-head">
        <h2>Despesas</h2>
        <div className="head-acoes">
          {(["xlsx", "csv"] as const).map((fmt) => (
            <button
              key={fmt}
              className="btn btn-sec"
              onClick={() =>
                baixar("/exportar/despesas", {
                  formato: fmt,
                  apartamento_id:
                    fApto === "" || fApto === "comum" ? undefined : fApto,
                  categoria: fCat || undefined,
                  inicio: fInicio || undefined,
                  fim: fFim || undefined,
                })
              }
            >
              Exportar {fmt === "xlsx" ? "Excel" : "CSV"}
            </button>
          ))}
          <button className="btn btn-primario" onClick={abrirNova}>
            + Nova despesa
          </button>
        </div>
      </div>

      <div className="filtros">
        <label>
          Apartamento
          <select value={fApto} onChange={(e) => setFApto(e.target.value)}>
            <option value="">Todos</option>
            <option value="comum">Comum / geral</option>
            {apartamentos.map((a) => (
              <option key={a.id} value={a.id}>
                {a.nome}
              </option>
            ))}
          </select>
        </label>
        <label>
          Categoria
          <select
            value={fCat}
            onChange={(e) => setFCat(e.target.value as CategoriaDespesa | "")}
          >
            <option value="">Todas</option>
            {CATEGORIAS.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </label>
        <label>
          Início
          <input type="date" value={fInicio} onChange={(e) => setFInicio(e.target.value)} />
        </label>
        <label>
          Fim
          <input type="date" value={fFim} onChange={(e) => setFFim(e.target.value)} />
        </label>
      </div>

      {erro && <div className="erro">{erro}</div>}

      <table className="tabela">
        <thead>
          <tr>
            <th>Data</th>
            <th>Apartamento</th>
            <th>Categoria</th>
            <th className="num">Valor</th>
            <th>Dedutível IR</th>
            <th>Observação</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {lista.map((d) => (
            <tr key={d.id}>
              <td>{dataBR(d.data)}</td>
              <td>{nomeApartamento(apartamentos, d.apartamento_id)}</td>
              <td>{d.categoria}</td>
              <td className="num">{moeda(d.valor)}</td>
              <td>{d.dedutivel_ir ? "Sim" : "Não"}</td>
              <td>{d.observacao}</td>
              <td className="acoes">
                <button className="btn-link" onClick={() => abrirEdicao(d)}>
                  Editar
                </button>
                <button className="btn-link perigo" onClick={() => excluir(d.id)}>
                  Excluir
                </button>
              </td>
            </tr>
          ))}
          {lista.length === 0 && (
            <tr>
              <td colSpan={7} className="vazio">
                Nenhuma despesa.
              </td>
            </tr>
          )}
        </tbody>
        {lista.length > 0 && (
          <tfoot>
            <tr>
              <td colSpan={3} className="num">
                <strong>Total</strong>
              </td>
              <td className="num">
                <strong>{moeda(total)}</strong>
              </td>
              <td colSpan={3}></td>
            </tr>
          </tfoot>
        )}
      </table>

      <Modal
        titulo={editId ? "Editar despesa" : "Nova despesa"}
        aberto={modalAberto}
        onClose={() => setModalAberto(false)}
      >
        <form className="form" onSubmit={salvar}>
          <div className="form-row">
            <label>
              Apartamento
              <select
                value={form.apartamento_id ?? ""}
                onChange={(e) =>
                  set(
                    "apartamento_id",
                    e.target.value === "" ? null : Number(e.target.value),
                  )
                }
              >
                <option value="">Comum / geral</option>
                {apartamentos.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.nome}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Data
              <input
                type="date"
                value={form.data}
                onChange={(e) => set("data", e.target.value)}
                required
              />
            </label>
          </div>
          <div className="form-row">
            <label>
              Categoria
              <select
                value={form.categoria}
                onChange={(e) => set("categoria", e.target.value as CategoriaDespesa)}
              >
                {CATEGORIAS.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </label>
            <label>
              Valor (R$)
              <input
                type="number"
                step="0.01"
                min={0}
                value={form.valor}
                onChange={(e) => set("valor", e.target.value)}
                required
              />
            </label>
          </div>
          <div className="form-row checks">
            <label className="check">
              <input
                type="checkbox"
                checked={form.dedutivel_ir}
                onChange={(e) => set("dedutivel_ir", e.target.checked)}
              />
              Dedutível no IR
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={form.recorrente}
                onChange={(e) => set("recorrente", e.target.checked)}
              />
              Recorrente
            </label>
          </div>
          <label>
            Observação
            <textarea
              value={form.observacao ?? ""}
              onChange={(e) => set("observacao", e.target.value)}
            />
          </label>
          {erroForm && <div className="erro">{erroForm}</div>}
          <div className="form-acoes">
            <button
              type="button"
              className="btn btn-sec"
              onClick={() => setModalAberto(false)}
            >
              Cancelar
            </button>
            <button type="submit" className="btn btn-primario">
              {editId ? "Salvar" : "Criar"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
