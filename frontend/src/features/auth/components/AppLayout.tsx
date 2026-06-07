import { useState } from "react";
import { Outlet, Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/shared/hooks/useAuth";

// ---------------------------------------------------------------------------
// region: Menu definition
// ---------------------------------------------------------------------------

type MenuSection = "principal" | "coordinacion" | "administracion";

interface MenuEntry {
  label: string;
  path: string;
  /** If set, the entry is only shown when the user has at least one of these. */
  permissions?: string[];
  icon: string; // SVG path data (simplified heroicons)
  section: MenuSection;
}

const menu_entries: MenuEntry[] = [
  {
    label: "Inicio",
    path: "/",
    section: "principal",
    icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6",
  },
  {
    label: "Mis Comisiones",
    path: "/comision",
    section: "principal",
    permissions: ["calificaciones:importar", "atrasados:ver"],
    icon: "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4",
  },
  {
    label: "Monitores",
    path: "/monitores",
    section: "principal",
    permissions: ["atrasados:ver"],
    icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
  },
  // ── Coordinación ────────────────────────────────────────────────────────
  {
    label: "Equipos Docentes",
    path: "/equipos",
    section: "coordinacion",
    permissions: ["equipos:asignar"],
    icon: "M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z",
  },
  {
    label: "Avisos",
    path: "/avisos",
    section: "coordinacion",
    permissions: ["avisos:publicar", "avisos:ver"],
    icon: "M3 4.5h18M3 9h18m-9 4.5h9M3 14.25h9m-4.5 4.5h4.5m-4.5 0l2.25-2.25m0 0l2.25 2.25M12 18.75l-2.25-2.25M12 18.75l2.25 2.25M3 4.5h18",
  },
  {
    label: "Tareas",
    path: "/tareas",
    section: "coordinacion",
    permissions: ["tareas:gestionar", "tareas:ver"],
    icon: "M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z",
  },
  {
    label: "Encuentros",
    path: "/encuentros",
    section: "coordinacion",
    permissions: ["encuentros:gestionar"],
    icon: "M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5m-9-6h.008v.008H12v-.008zM12 15h.008v.008H12V15zm0 2.25h.008v.008H12v-.008zM9.75 15h.008v.008H9.75V15zm0 2.25h.008v.008H9.75v-.008zM7.5 15h.008v.008H7.5V15zm0 2.25h.008v.008H7.5v-.008zm6.75-4.5h.008v.008h-.008v-.008zm0 2.25h.008v.008h-.008V15zm0 2.25h.008v.008h-.008v-.008zm2.25-4.5h.008v.008H16.5v-.008zm0 2.25h.008v.008H16.5V15z",
  },
  {
    label: "Coloquios",
    path: "/coloquios",
    section: "coordinacion",
    permissions: ["coloquios:gestionar", "coloquios:reservar"],
    icon: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  },
  {
    label: "Comunicaciones",
    path: "/comunicaciones",
    section: "coordinacion",
    permissions: ["comunicacion:enviar"],
    icon: "M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75",
  },
  {
    label: "Guardias",
    path: "/guardias",
    section: "coordinacion",
    permissions: ["guardias:ver"],
    icon: "M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z",
  },
  // ── Administración ─────────────────────────────────────────────────────
  {
    label: "Estructura Académica",
    path: "/estructura",
    section: "administracion",
    permissions: ["estructura:gestionar"],
    icon: "M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21",
  },
  {
    label: "Usuarios",
    path: "/usuarios",
    section: "administracion",
    permissions: ["usuarios:gestionar"],
    icon: "M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z",
  },
  {
    label: "Auditoría",
    path: "/auditoria",
    section: "administracion",
    permissions: ["auditoria:ver"],
    icon: "M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z",
  },
  {
    label: "Liquidaciones",
    path: "/liquidaciones",
    section: "administracion",
    permissions: ["liquidaciones:ver"],
    icon: "M2.25 18.75a60.07 60.07 0 0115.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 013 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125V9M7.5 12h.008v.008H7.5V12zm3 0h.008v.008H10.5V12zm3 0h.008v.008H13.5V12zm0 3h.008v.008H13.5V15z",
  },
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

  const grouped_entries = visible_entries.reduce<
    Record<string, MenuEntry[]>
  >((acc, entry) => {
    if (!acc[entry.section]) acc[entry.section] = [];
    acc[entry.section]!.push(entry);
    return acc;
  }, {});

  const section_labels: Record<string, string> = {
    principal: "Principal",
    coordinacion: "Coordinación",
    administracion: "Administración",
  };

  const section_order = ["principal", "coordinacion", "administracion"];

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
            {section_order.map((section_key) => {
              const section_entries = grouped_entries[section_key];
              if (!section_entries || section_entries.length === 0) return null;
              const is_first = section_key === "principal";
              return (
                <li key={section_key}>
                  {!is_first && (
                    <div className="mb-2 mt-4 border-t pt-3">
                      <p className="px-1 text-xs font-semibold uppercase tracking-wider text-gray-400">
                        {section_labels[section_key]}
                      </p>
                    </div>
                  )}
                  <ul className="space-y-1">
                    {section_entries.map((entry) => {
                      const is_active = location.pathname.startsWith(entry.path) && (
                        entry.path === "/"
                          ? location.pathname === "/"
                          : true
                      );
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


