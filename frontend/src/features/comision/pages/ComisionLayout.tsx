import { Outlet, NavLink, useParams } from "react-router-dom";

const sub_nav = [
  { label: "Atrasados", path: "atrasados" },
  { label: "Rankings", path: "rankings" },
  { label: "Reportes", path: "reportes" },
  { label: "Importar", path: "importar" },
  { label: "Umbral", path: "umbral" },
  { label: "Comunicaciones", path: "comunicaciones" },
];

export function ComisionLayout() {
  const { materiaId } = useParams<{ materiaId: string }>();

  return (
    <div className="space-y-6">
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-4 overflow-x-auto" aria-label="Tabs">
          {sub_nav.map((item) => (
            <NavLink
              key={item.path}
              to={`/comision/${materiaId}/${item.path}`}
              className={({ isActive }) =>
                `whitespace-nowrap border-b-2 px-1 py-3 text-sm font-medium transition-colors ${
                  isActive
                    ? "border-brand-600 text-brand-700"
                    : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </div>

      <Outlet />
    </div>
  );
}
