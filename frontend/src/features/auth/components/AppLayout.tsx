import { useState } from "react";
import { Outlet, Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/shared/hooks/useAuth";

// ---------------------------------------------------------------------------
// region: Menu definition
// ---------------------------------------------------------------------------

interface MenuEntry {
  label: string;
  path: string;
  /** If set, the entry is only shown when the user has at least one of these. */
  permissions?: string[];
  icon: string; // SVG path data (simplified heroicons)
}

const menu_entries: MenuEntry[] = [
  {
    label: "Inicio",
    path: "/",
    icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6",
  },
  {
    label: "Mis Comisiones",
    path: "/comision",
    permissions: ["calificaciones:importar", "atrasados:ver"],
    icon: "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4",
  },
  {
    label: "Monitores",
    path: "/monitores",
    permissions: ["atrasados:ver"],
    icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
  },
  // ── Features de cambios futuros (C-23+). Re-activar cuando se implementen ──
  // {
  //   label: "Equipos Docentes",
  //   path: "/equipos",
  //   permissions: ["equipos:asignar"],
  //   icon: "…",
  // },
  // {
  //   label: "Avisos",
  //   path: "/avisos",
  //   permissions: ["avisos:publicar", "avisos:ver"],
  //   icon: "…",
  // },
  // {
  //   label: "Tareas",
  //   path: "/tareas",
  //   permissions: ["tareas:gestionar", "tareas:ver"],
  //   icon: "…",
  // },
  // {
  //   label: "Encuentros",
  //   path: "/encuentros",
  //   permissions: ["encuentros:gestionar"],
  //   icon: "…",
  // },
  // {
  //   label: "Coloquios",
  //   path: "/coloquios",
  //   permissions: ["coloquios:gestionar", "coloquios:reservar"],
  //   icon: "…",
  // },
  // {
  //   label: "Comunicaciones",
  //   path: "/comunicaciones",
  //   permissions: ["comunicacion:enviar"],
  //   icon: "…",
  // },
  // {
  //   label: "Estructura Académica",
  //   path: "/estructura",
  //   permissions: ["estructura:gestionar"],
  //   icon: "…",
  // },
  // {
  //   label: "Usuarios",
  //   path: "/usuarios",
  //   permissions: ["usuarios:gestionar"],
  //   icon: "…",
  // },
  // {
  //   label: "Auditoría",
  //   path: "/auditoria",
  //   permissions: ["auditoria:ver"],
  //   icon: "…",
  // },
  // {
  //   label: "Liquidaciones",
  //   path: "/liquidaciones",
  //   permissions: ["liquidaciones:ver"],
  //   icon: "…",
  // },
];

// ---------------------------------------------------------------------------
// endregion
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// region: Sidebar
// ---------------------------------------------------------------------------

function Sidebar({
  is_open,
  on_close,
  on_menu_toggle,
}: {
  is_open: boolean;
  on_close: () => void;
  on_menu_toggle: () => void;
}) {
  const { permissions, user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const is_admin = user?.roles?.includes("ADMIN") ?? false;

  const handle_logout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  const visible_entries = menu_entries.filter((entry) => {
    if (!entry.permissions || entry.permissions.length === 0) return true;
    return entry.permissions.some((p) => permissions.includes(p));
  });

  return (
    <>
      {/* Mobile overlay */}
      {is_open && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={on_close}
          aria-hidden="true"
        />
      )}

      {/* Mobile floating menu button for admin (no header) */}
      {is_admin && !is_open && (
        <button
          type="button"
          className="fixed left-4 top-4 z-50 rounded-md bg-white p-2 text-gray-500 shadow-lg hover:bg-gray-100 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-500 lg:hidden"
          onClick={on_menu_toggle}
          aria-label="Abrir menú"
        >
          <svg
            className="h-6 w-6"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
            />
          </svg>
        </button>
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-white shadow-lg transition-transform duration-200 lg:static lg:translate-x-0 ${
          is_open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Brand */}
        <div className="flex h-16 items-center gap-2 border-b px-6">
          <span className="text-xl font-bold text-brand-700">trace</span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-3 py-4">
          <ul className="space-y-1">
            {visible_entries.map((entry) => {
              const is_active = location.pathname === entry.path;
              return (
                <li key={entry.path}>
                  <Link
                    to={entry.path}
                    onClick={on_close}
                    className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                      is_active
                        ? "bg-brand-50 text-brand-700"
                        : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                    }`}
                  >
                    <svg
                      className="h-5 w-5 flex-shrink-0"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={1.5}
                      stroke="currentColor"
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d={entry.icon}
                      />
                    </svg>
                    {entry.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Admin user footer — only when header is hidden */}
        {is_admin && (
          <div className="border-t px-3 py-4">
            <div className="mb-3 text-center">
              <p className="text-sm font-medium text-gray-900">
                {user?.nombre ?? "Admin"}
              </p>
              <p className="text-xs text-gray-500">{user?.email ?? ""}</p>
            </div>
            <button
              type="button"
              onClick={handle_logout}
              className="flex w-full items-center justify-center gap-2 rounded-md px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <svg
                className="h-4 w-4"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9"
                />
              </svg>
              Cerrar sesión
            </button>
          </div>
        )}
      </aside>
    </>
  );
}

// ---------------------------------------------------------------------------
// endregion
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// region: Header
// ---------------------------------------------------------------------------

function Header({ on_menu_toggle }: { on_menu_toggle: () => void }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handle_logout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className="flex h-16 items-center justify-between border-b bg-white px-4 lg:px-6">
      {/* Mobile menu button */}
      <button
        type="button"
        className="rounded-md p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-500 lg:hidden"
        onClick={on_menu_toggle}
        aria-label="Abrir menú"
      >
        <svg
          className="h-6 w-6"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
          />
        </svg>
      </button>

      {/* Spacer on desktop */}
      <div className="hidden lg:block" />

      {/* User info */}
      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="text-sm font-medium text-gray-900">
            {user?.nombre ?? "Usuario"}
          </p>
          <p className="text-xs text-gray-500">{user?.email ?? ""}</p>
        </div>
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-100 text-sm font-semibold text-brand-700">
          {(user?.nombre ?? "U").charAt(0).toUpperCase()}
        </div>
        <button
          type="button"
          onClick={handle_logout}
          className="rounded-md px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          Cerrar sesión
        </button>
      </div>
    </header>
  );
}

// ---------------------------------------------------------------------------
// endregion
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// region: AppLayout
// ---------------------------------------------------------------------------

export function AppLayout() {
  const [sidebar_open, set_sidebar_open] = useState(false);
  const { user } = useAuth();
  const is_admin = user?.roles?.includes("ADMIN") ?? false;

  return (
    <div className="flex min-h-screen">
      <Sidebar
        is_open={sidebar_open}
        on_close={() => set_sidebar_open(false)}
        on_menu_toggle={() => set_sidebar_open((prev) => !prev)}
      />
      <div className="flex flex-1 flex-col">
        {!is_admin && (
          <Header on_menu_toggle={() => set_sidebar_open((prev) => !prev)} />
        )}
        <main className={`flex-1 overflow-y-auto ${is_admin ? "" : ""} p-6`}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// endregion
// ---------------------------------------------------------------------------


