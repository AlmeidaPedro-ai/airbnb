// Cliente HTTP simples com JWT em localStorage.

const TOKEN_KEY = "airbnb_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  params?: Record<string, string | number | undefined | null>;
}

function buildQuery(params?: RequestOptions["params"]): string {
  if (!params) return "";
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") usp.append(k, String(v));
  }
  const q = usp.toString();
  return q ? `?${q}` : "";
}

export async function api<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body, params } = options;
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const resp = await fetch(`/api${path}${buildQuery(params)}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (resp.status === 401) {
    setToken(null);
    if (!path.startsWith("/auth/login")) {
      window.location.hash = "#/login";
    }
    throw new ApiError(401, "Sessão expirada. Faça login novamente.");
  }

  if (!resp.ok) {
    let detail = `Erro ${resp.status}`;
    try {
      const data = await resp.json();
      if (data?.detail) {
        detail =
          typeof data.detail === "string"
            ? data.detail
            : JSON.stringify(data.detail);
      }
    } catch {
      /* corpo vazio */
    }
    throw new ApiError(resp.status, detail);
  }

  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

/** Envia multipart/form-data (upload de arquivo) com JWT. */
export async function apiForm<T>(path: string, form: FormData): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const resp = await fetch(`/api${path}`, { method: "POST", headers, body: form });
  if (!resp.ok) {
    let detail = `Erro ${resp.status}`;
    try {
      const data = await resp.json();
      if (data?.detail)
        detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } catch {
      /* vazio */
    }
    throw new ApiError(resp.status, detail);
  }
  return (await resp.json()) as T;
}

/** Baixa um arquivo de um endpoint protegido (fetch + blob + <a download>). */
export async function baixar(
  path: string,
  params?: Record<string, string | number | undefined | null>,
): Promise<void> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const resp = await fetch(`/api${path}${buildQuery(params)}`, { headers });
  if (!resp.ok) throw new ApiError(resp.status, `Falha ao exportar (${resp.status}).`);

  const disp = resp.headers.get("Content-Disposition") || "";
  const m = disp.match(/filename="?([^"]+)"?/);
  const nome = m ? m[1] : "export";
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nome;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
