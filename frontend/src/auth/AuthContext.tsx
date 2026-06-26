import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, getToken, setToken } from "../api/client";

interface AuthState {
  autenticado: boolean;
  email: string | null;
  login: (email: string, senha: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

interface MeResponse {
  id: number;
  email: string;
  ativo: boolean;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [autenticado, setAutenticado] = useState<boolean>(!!getToken());
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    if (autenticado && !email) {
      api<MeResponse>("/auth/me")
        .then((u) => setEmail(u.email))
        .catch(() => {
          setToken(null);
          setAutenticado(false);
        });
    }
  }, [autenticado, email]);

  const value = useMemo<AuthState>(
    () => ({
      autenticado,
      email,
      async login(emailIn, senha) {
        const resp = await api<TokenResponse>("/auth/login", {
          method: "POST",
          body: { email: emailIn, senha },
        });
        setToken(resp.access_token);
        setAutenticado(true);
        setEmail(emailIn);
      },
      logout() {
        setToken(null);
        setAutenticado(false);
        setEmail(null);
      },
    }),
    [autenticado, email],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth fora de AuthProvider");
  return ctx;
}
