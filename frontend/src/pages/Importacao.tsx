import { useState, type ChangeEvent } from "react";
import { apiForm } from "../api/client";
import { useApartamentos } from "../components/useApartamentos";
import {
  ROTULO_CAMPO,
  type ImportAnalise,
  type PreviaImportacao,
} from "../api/types";
import { dataBR, moeda } from "../utils/format";

export default function Importacao() {
  const { apartamentos } = useApartamentos();
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [analise, setAnalise] = useState<ImportAnalise | null>(null);
  const [mapeamento, setMapeamento] = useState<Record<string, string>>({});
  const [dePara, setDePara] = useState<Record<string, number | "">>({});
  const [previa, setPrevia] = useState<PreviaImportacao | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  function escolherArquivo(e: ChangeEvent<HTMLInputElement>) {
    setArquivo(e.target.files?.[0] ?? null);
    setAnalise(null);
    setPrevia(null);
    setErro(null);
    setOk(null);
  }

  async function analisar() {
    if (!arquivo) return;
    setErro(null);
    setOk(null);
    setOcupado(true);
    try {
      const fd = new FormData();
      fd.append("arquivo", arquivo);
      const a = await apiForm<ImportAnalise>("/importar/reservas/analisar", fd);
      setAnalise(a);
      const mp: Record<string, string> = {};
      for (const campo of a.campos) mp[campo] = a.sugestao_mapeamento[campo] ?? "";
      setMapeamento(mp);
      setDePara(Object.fromEntries(a.listings.map((l) => [l, ""])));
      setPrevia(null);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao analisar");
    } finally {
      setOcupado(false);
    }
  }

  function montarForm(dryRun: boolean): FormData {
    const fd = new FormData();
    fd.append("arquivo", arquivo as File);
    const mapaLimpo: Record<string, string | null> = {};
    for (const [k, v] of Object.entries(mapeamento)) mapaLimpo[k] = v || null;
    const dp: Record<string, number> = {};
    for (const [k, v] of Object.entries(dePara)) if (v !== "") dp[k] = v as number;
    fd.append("mapeamento", JSON.stringify(mapaLimpo));
    fd.append("de_para", JSON.stringify(dp));
    fd.append("dry_run", dryRun ? "true" : "false");
    return fd;
  }

  async function executar(dryRun: boolean) {
    if (!arquivo) return;
    setErro(null);
    setOk(null);
    setOcupado(true);
    try {
      const p = await apiForm<PreviaImportacao>(
        "/importar/reservas/confirmar",
        montarForm(dryRun),
      );
      setPrevia(p);
      if (!dryRun) setOk(`${p.importadas} reserva(s) importada(s) com sucesso.`);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao processar");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div>
      <div className="page-head">
        <h2>Importar reservas (CSV do Airbnb)</h2>
      </div>

      <div className="disclaimer">
        Exporte o CSV de reservas do Airbnb (não fazemos scraping do site) e
        importe aqui. O cabeçalho muda por idioma/versão — confira o mapeamento de
        colunas e associe cada anúncio a um apartamento antes de importar.
      </div>

      <div className="card">
        <h3>1. Arquivo</h3>
        <input type="file" accept=".csv,text/csv" onChange={escolherArquivo} />
        <button
          className="btn btn-primario"
          style={{ marginLeft: 12 }}
          disabled={!arquivo || ocupado}
          onClick={analisar}
        >
          Analisar
        </button>
      </div>

      {erro && <div className="erro">{erro}</div>}
      {ok && <div className="info sucesso">{ok}</div>}

      {analise && (
        <>
          <div className="card">
            <h3>2. Mapeamento de colunas</h3>
            <p className="ajuda">
              {analise.total_linhas} linha(s) no arquivo. Campos obrigatórios:{" "}
              {analise.obrigatorios.map((c) => ROTULO_CAMPO[c]).join(", ")}.
            </p>
            <div className="grid-mapeamento">
              {analise.campos.map((campo) => (
                <label key={campo}>
                  {ROTULO_CAMPO[campo]}
                  {analise.obrigatorios.includes(campo) && (
                    <span className="obrig"> *</span>
                  )}
                  <select
                    value={mapeamento[campo] ?? ""}
                    onChange={(e) =>
                      setMapeamento((m) => ({ ...m, [campo]: e.target.value }))
                    }
                  >
                    <option value="">— ignorar —</option>
                    {analise.colunas.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
          </div>

          <div className="card">
            <h3>3. De-para de anúncios → apartamentos</h3>
            {analise.listings.length === 0 ? (
              <p className="ajuda">
                Nenhum anúncio detectado (verifique a coluna mapeada como
                "Anúncio").
              </p>
            ) : (
              <table className="tabela">
                <thead>
                  <tr>
                    <th>Anúncio no CSV</th>
                    <th>Apartamento</th>
                  </tr>
                </thead>
                <tbody>
                  {analise.listings.map((l) => (
                    <tr key={l}>
                      <td>{l}</td>
                      <td>
                        <select
                          value={dePara[l] ?? ""}
                          onChange={(e) =>
                            setDePara((d) => ({
                              ...d,
                              [l]: e.target.value === "" ? "" : Number(e.target.value),
                            }))
                          }
                        >
                          <option value="">— não importar —</option>
                          {apartamentos.map((a) => (
                            <option key={a.id} value={a.id}>
                              {a.nome}
                            </option>
                          ))}
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="form-acoes esquerda">
            <button
              className="btn btn-sec"
              disabled={ocupado}
              onClick={() => executar(true)}
            >
              Pré-visualizar (dry-run)
            </button>
            {previa && previa.criar > 0 && (
              <button
                className="btn btn-primario"
                disabled={ocupado}
                onClick={() => executar(false)}
              >
                Importar {previa.criar} reserva(s)
              </button>
            )}
          </div>
        </>
      )}

      {previa && (
        <div className="card">
          <h3>
            {previa.dry_run ? "Pré-visualização" : "Resultado da importação"}
          </h3>
          <div className="resumo-import">
            <span className="badge criar">Criar: {previa.criar}</span>
            <span className="badge ignorar">Ignorar: {previa.ignorar}</span>
            <span className="badge erro">Erros: {previa.erro}</span>
            {!previa.dry_run && (
              <span className="badge ok">Importadas: {previa.importadas}</span>
            )}
          </div>
          <table className="tabela">
            <thead>
              <tr>
                <th className="num">#</th>
                <th>Ação</th>
                <th>Anúncio</th>
                <th>Check-in</th>
                <th>Check-out</th>
                <th className="num">Hósp.</th>
                <th className="num">Valor</th>
                <th>Motivo</th>
              </tr>
            </thead>
            <tbody>
              {previa.linhas.map((l) => (
                <tr key={l.indice} className={`linha-${l.acao}`}>
                  <td className="num">{l.indice}</td>
                  <td>{l.acao}</td>
                  <td>{l.listing}</td>
                  <td>{dataBR(l.check_in)}</td>
                  <td>{dataBR(l.check_out)}</td>
                  <td className="num">{l.num_hospedes ?? ""}</td>
                  <td className="num">
                    {l.valor_hospedagem != null ? moeda(l.valor_hospedagem) : ""}
                  </td>
                  <td>{l.motivo}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
