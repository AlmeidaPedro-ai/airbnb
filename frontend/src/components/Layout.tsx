import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const LINKS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/reservas", label: "Reservas", end: false },
  { to: "/despesas", label: "Despesas", end: false },
  { to: "/apartamentos", label: "Apartamentos", end: false },
  { to: "/imposto", label: "Imposto", end: false },
  { to: "/importar", label: "Importar CSV", end: false },
  { to: "/parametros-ir", label: "Parâmetros IR", end: false },
];

export default function Layout() {
  const { email, logout } = useAuth();
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          🏠 Locação
          <span className="brand-sub">Temporada · RJ</span>
        </div>
        <nav>
          {LINKS.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) => (isActive ? "nav-item ativo" : "nav-item")}
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="user-email" title={email ?? ""}>
            {email}
          </div>
          <button className="btn-link" onClick={logout}>
            Sair
          </button>
        </div>
      </aside>
      <main className="conteudo">
        <Outlet />
      </main>
    </div>
  );
}
