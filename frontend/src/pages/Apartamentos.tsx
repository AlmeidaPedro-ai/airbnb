import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import Modal from "../components/Modal";
import type { Apartamento, ApartamentoInput } from "../api/types";
import { dataBR } from "../utils/format";

const VAZIO: ApartamentoInput = {
  nome: "",
  endereco: "",
  quartos: 1,
  capacidade: 2,
  data_inicio_operacao: new Date().toISOString().slice(0, 10),
  ativo: true,
};

export default function Apartamentos() {
  const [lista, setLista] = useState<Apartamento[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const [modalAberto, setModalAberto] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<ApartamentoInput>(VAZIO);
  const [erroForm, setErroForm] = useState<string | null>(null);

  const carregar = useCallback(() => {
    setErro(null);
    api<Apartamento[]>("/apartamentos").then(setLista).catch((e) => setErro(e.message));
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  function abrirNova() {
    setEditId(null);
    setForm(VAZIO);
    setErroForm(null);
    setModalAberto(true);
  }

  function abrirEdicao(a: Apartamento) {
    setEditId(a.id);
    setForm({
      nome: a.nome,
      endereco: a.endereco ?? "",
      quartos: a.quartos,
      capacidade: a.capacidade,
      data_inicio_operacao: a.data_inicio_operacao,
      ativo: a.ativo,
    });
    setErroForm(null);
    setModalAberto(true);
  }

  async function salvar(e: FormEvent) {
    e.preventDefault();
    setErroForm(null);
    try {
      if (editId) {
        await api(`/apartamentos/${editId}`, { method: "PUT", body: form });
      } else {
        await api("/apartamentos", { method: "POST", body: form });
      }
      setModalAberto(false);
      carregar();
    } catch (err) {
      setErroForm(err instanceof Error ? err.message : "Erro ao salvar");
    }
  }

  async function excluir(a: Apartamento) {
    if (!confirm(`Excluir "${a.nome}"?`)) return;
    try {
      await api(`/apartamentos/${a.id}`, { method: "DELETE" });
      carregar();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erro ao excluir");
    }
  }

  function set<K extends keyof ApartamentoInput>(k: K, v: ApartamentoInput[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  return (
    <div>
      <div className="page-head">
        <h2>Apartamentos</h2>
        <button className="btn btn-primario" onClick={abrirNova}>
          + Novo apartamento
        </button>
      </div>

      {erro && <div className="erro">{erro}</div>}

      <table className="tabela">
        <thead>
          <tr>
            <th>Nome</th>
            <th>Endereço</th>
            <th className="num">Quartos</th>
            <th className="num">Capacidade</th>
            <th>Início operação</th>
            <th>Ativo</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {lista.map((a) => (
            <tr key={a.id}>
              <td>{a.nome}</td>
              <td>{a.endereco}</td>
              <td className="num">{a.quartos}</td>
              <td className="num">{a.capacidade}</td>
              <td>{dataBR(a.data_inicio_operacao)}</td>
              <td>{a.ativo ? "Sim" : "Não"}</td>
              <td className="acoes">
                <button className="btn-link" onClick={() => abrirEdicao(a)}>
                  Editar
                </button>
                <button className="btn-link perigo" onClick={() => excluir(a)}>
                  Excluir
                </button>
              </td>
            </tr>
          ))}
          {lista.length === 0 && (
            <tr>
              <td colSpan={7} className="vazio">
                Nenhum apartamento.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <Modal
        titulo={editId ? "Editar apartamento" : "Novo apartamento"}
        aberto={modalAberto}
        onClose={() => setModalAberto(false)}
      >
        <form className="form" onSubmit={salvar}>
          <label>
            Nome
            <input
              value={form.nome}
              onChange={(e) => set("nome", e.target.value)}
              required
            />
          </label>
          <label>
            Endereço
            <input
              value={form.endereco ?? ""}
              onChange={(e) => set("endereco", e.target.value)}
            />
          </label>
          <div className="form-row">
            <label>
              Quartos
              <input
                type="number"
                min={0}
                value={form.quartos}
                onChange={(e) => set("quartos", Number(e.target.value))}
              />
            </label>
            <label>
              Capacidade
              <input
                type="number"
                min={1}
                value={form.capacidade}
                onChange={(e) => set("capacidade", Number(e.target.value))}
              />
            </label>
            <label>
              Início operação
              <input
                type="date"
                value={form.data_inicio_operacao}
                onChange={(e) => set("data_inicio_operacao", e.target.value)}
                required
              />
            </label>
          </div>
          <label className="check">
            <input
              type="checkbox"
              checked={form.ativo}
              onChange={(e) => set("ativo", e.target.checked)}
            />
            Ativo
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
