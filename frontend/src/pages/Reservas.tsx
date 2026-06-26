import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, baixar } from "../api/client";
import Modal from "../components/Modal";
import { nomeApartamento, useApartamentos } from "../components/useApartamentos";
import {
  CANAIS,
  STATUS_RESERVA,
  type Reserva,
  type ReservaInput,
  type ReservaResult,
} from "../api/types";
import { dataBR, moeda } from "../utils/format";

const VAZIO: ReservaInput = {
  apartamento_id: 0,
  check_in: "",
  check_out: "",
  num_hospedes: 1,
  valor_hospedagem: "0",
  taxa_limpeza: "0",
  comissao: "0",
  canal: "Airbnb",
  status: "Confirmada",
  codigo_confirmacao: "",
  observacao: "",
};

export default function Reservas() {
  const { apartamentos } = useApartamentos();
  const [lista, setLista] = useState<Reserva[]>([]);
  const [fApto, setFApto] = useState<number | "">("");
  const [fInicio, setFInicio] = useState("");
  const [fFim, setFFim] = useState("");
  const [erro, setErro] = useState<string | null>(null);

  const [modalAberto, setModalAberto] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<ReservaInput>(VAZIO);
  const [avisos, setAvisos] = useState<string[]>([]);
  const [erroForm, setErroForm] = useState<string | null>(null);

  const carregar = useCallback(() => {
    setErro(null);
    api<Reserva[]>("/reservas", {
      params: {
        apartamento_id: fApto === "" ? undefined : fApto,
        inicio: fInicio || undefined,
        fim: fFim || undefined,
      },
    })
      .then(setLista)
      .catch((e) => setErro(e.message));
  }, [fApto, fInicio, fFim]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  function abrirNova() {
    setEditId(null);
    setForm({ ...VAZIO, apartamento_id: apartamentos[0]?.id ?? 0 });
    setAvisos([]);
    setErroForm(null);
    setModalAberto(true);
  }

  function abrirEdicao(r: Reserva) {
    setEditId(r.id);
    setForm({
      apartamento_id: r.apartamento_id,
      check_in: r.check_in,
      check_out: r.check_out,
      num_hospedes: r.num_hospedes,
      valor_hospedagem: r.valor_hospedagem,
      taxa_limpeza: r.taxa_limpeza,
      comissao: r.comissao,
      canal: r.canal,
      status: r.status,
      codigo_confirmacao: r.codigo_confirmacao ?? "",
      observacao: r.observacao ?? "",
    });
    setAvisos([]);
    setErroForm(null);
    setModalAberto(true);
  }

  async function salvar(e: FormEvent) {
    e.preventDefault();
    setErroForm(null);
    try {
      const result = editId
        ? await api<ReservaResult>(`/reservas/${editId}`, {
            method: "PUT",
            body: form,
          })
        : await api<ReservaResult>("/reservas", { method: "POST", body: form });
      setAvisos(result.avisos);
      carregar();
      if (result.avisos.length === 0) setModalAberto(false);
    } catch (err) {
      setErroForm(err instanceof Error ? err.message : "Erro ao salvar");
    }
  }

  async function excluir(id: number) {
    if (!confirm("Excluir esta reserva?")) return;
    await api(`/reservas/${id}`, { method: "DELETE" });
    carregar();
  }

  function set<K extends keyof ReservaInput>(k: K, v: ReservaInput[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  return (
    <div>
      <div className="page-head">
        <h2>Reservas</h2>
        <div className="head-acoes">
          <button
            className="btn btn-sec"
            onClick={() =>
              baixar("/exportar/reservas", {
                formato: "xlsx",
                apartamento_id: fApto === "" ? undefined : fApto,
                inicio: fInicio || undefined,
                fim: fFim || undefined,
              })
            }
          >
            Exportar Excel
          </button>
          <button
            className="btn btn-sec"
            onClick={() =>
              baixar("/exportar/reservas", {
                formato: "csv",
                apartamento_id: fApto === "" ? undefined : fApto,
                inicio: fInicio || undefined,
                fim: fFim || undefined,
              })
            }
          >
            Exportar CSV
          </button>
          <button className="btn btn-primario" onClick={abrirNova}>
            + Nova reserva
          </button>
        </div>
      </div>

      <div className="filtros">
        <label>
          Apartamento
          <select
            value={fApto}
            onChange={(e) =>
              setFApto(e.target.value === "" ? "" : Number(e.target.value))
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
            <th>Apartamento</th>
            <th>Check-in</th>
            <th>Check-out</th>
            <th className="num">Noites</th>
            <th className="num">Hósp.</th>
            <th className="num">Hospedagem</th>
            <th className="num">Líquida</th>
            <th>Canal</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {lista.map((r) => (
            <tr key={r.id}>
              <td>{nomeApartamento(apartamentos, r.apartamento_id)}</td>
              <td>{dataBR(r.check_in)}</td>
              <td>{dataBR(r.check_out)}</td>
              <td className="num">{r.noites}</td>
              <td className="num">{r.num_hospedes}</td>
              <td className="num">{moeda(r.valor_hospedagem)}</td>
              <td className="num">{moeda(r.receita_liquida)}</td>
              <td>{r.canal}</td>
              <td>
                <span className={`tag tag-${r.status.toLowerCase()}`}>{r.status}</span>
              </td>
              <td className="acoes">
                <button className="btn-link" onClick={() => abrirEdicao(r)}>
                  Editar
                </button>
                <button className="btn-link perigo" onClick={() => excluir(r.id)}>
                  Excluir
                </button>
              </td>
            </tr>
          ))}
          {lista.length === 0 && (
            <tr>
              <td colSpan={10} className="vazio">
                Nenhuma reserva.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <Modal
        titulo={editId ? "Editar reserva" : "Nova reserva"}
        aberto={modalAberto}
        onClose={() => setModalAberto(false)}
      >
        <form className="form" onSubmit={salvar}>
          <label>
            Apartamento
            <select
              value={form.apartamento_id}
              onChange={(e) => set("apartamento_id", Number(e.target.value))}
              required
            >
              {apartamentos.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.nome} (cap. {a.capacidade})
                </option>
              ))}
            </select>
          </label>
          <div className="form-row">
            <label>
              Check-in
              <input
                type="date"
                value={form.check_in}
                onChange={(e) => set("check_in", e.target.value)}
                required
              />
            </label>
            <label>
              Check-out
              <input
                type="date"
                value={form.check_out}
                onChange={(e) => set("check_out", e.target.value)}
                required
              />
            </label>
            <label>
              Hóspedes
              <input
                type="number"
                min={1}
                value={form.num_hospedes}
                onChange={(e) => set("num_hospedes", Number(e.target.value))}
                required
              />
            </label>
          </div>
          <div className="form-row">
            <label>
              Hospedagem (R$)
              <input
                type="number"
                step="0.01"
                min={0}
                value={form.valor_hospedagem}
                onChange={(e) => set("valor_hospedagem", e.target.value)}
                required
              />
            </label>
            <label>
              Taxa limpeza (R$)
              <input
                type="number"
                step="0.01"
                min={0}
                value={form.taxa_limpeza}
                onChange={(e) => set("taxa_limpeza", e.target.value)}
              />
            </label>
            <label>
              Comissão (R$)
              <input
                type="number"
                step="0.01"
                min={0}
                value={form.comissao}
                onChange={(e) => set("comissao", e.target.value)}
              />
            </label>
          </div>
          <div className="form-row">
            <label>
              Canal
              <select
                value={form.canal}
                onChange={(e) => set("canal", e.target.value as ReservaInput["canal"])}
              >
                {CANAIS.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </label>
            <label>
              Status
              <select
                value={form.status}
                onChange={(e) =>
                  set("status", e.target.value as ReservaInput["status"])
                }
              >
                {STATUS_RESERVA.map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
            </label>
            <label>
              Cód. confirmação
              <input
                value={form.codigo_confirmacao ?? ""}
                onChange={(e) => set("codigo_confirmacao", e.target.value)}
              />
            </label>
          </div>
          <label>
            Observação
            <textarea
              value={form.observacao ?? ""}
              onChange={(e) => set("observacao", e.target.value)}
            />
          </label>

          {avisos.length > 0 && (
            <div className="avisos">
              <strong>Atenção (não bloqueante):</strong>
              <ul>
                {avisos.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
              <small>Os dados já foram salvos. Feche ou ajuste se necessário.</small>
            </div>
          )}
          {erroForm && <div className="erro">{erroForm}</div>}

          <div className="form-acoes">
            <button
              type="button"
              className="btn btn-sec"
              onClick={() => setModalAberto(false)}
            >
              Fechar
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
