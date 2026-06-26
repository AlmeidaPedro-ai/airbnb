import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Reservas from "./pages/Reservas";
import Despesas from "./pages/Despesas";
import Apartamentos from "./pages/Apartamentos";
import Imposto from "./pages/Imposto";
import ParametrosIR from "./pages/ParametrosIR";
import type { ReactNode } from "react";

function Protegida({ children }: { children: ReactNode }) {
  const { autenticado } = useAuth();
  return autenticado ? <>{children}</> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <Protegida>
            <Layout />
          </Protegida>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/reservas" element={<Reservas />} />
        <Route path="/despesas" element={<Despesas />} />
        <Route path="/apartamentos" element={<Apartamentos />} />
        <Route path="/imposto" element={<Imposto />} />
        <Route path="/parametros-ir" element={<ParametrosIR />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
