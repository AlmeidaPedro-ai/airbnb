import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Apartamento } from "../api/types";

/** Carrega a lista de apartamentos (cacheada por montagem do componente). */
export function useApartamentos(apenasAtivos = false) {
  const [apartamentos, setApartamentos] = useState<Apartamento[]>([]);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    let vivo = true;
    api<Apartamento[]>("/apartamentos", {
      params: { apenas_ativos: apenasAtivos ? "true" : undefined },
    })
      .then((a) => {
        if (vivo) setApartamentos(a);
      })
      .finally(() => {
        if (vivo) setCarregando(false);
      });
    return () => {
      vivo = false;
    };
  }, [apenasAtivos]);

  return { apartamentos, carregando };
}

export function nomeApartamento(
  apartamentos: Apartamento[],
  id: number | null,
): string {
  if (id === null) return "Comum / geral";
  return apartamentos.find((a) => a.id === id)?.nome ?? `#${id}`;
}
