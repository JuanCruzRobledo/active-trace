import { Outlet, NavLink } from "react-router-dom";

const sub_nav = [
  { label: "Mis Equipos", path: "mis-equipos" },
  { label: "Asignaciones", path: "asignaciones" },
  { label: "Asignación Masiva", path: "asignacion-masiva" },
  { label: "Clonar", path: "clonar" },
  { label: "Vigencia", path: "vigencia" },
  { label: "Exportar", path: "exportar" },
];

export function EquiposLayout() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Equipos Docentes</h1>
        <p className="mt-1 text-sm text-gray-500">
          Gestión de equipos docentes por materia, carrera y cohorte
        </p>
      </div>

      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-4 overflow-x-auto" aria-label="Tabs">
          {sub_nav.map((item) => (
            <NavLink
              key={item.path}
              to={`/equipos/${item.path}`}
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
