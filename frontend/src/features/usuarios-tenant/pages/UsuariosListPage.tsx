import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  useUsuariosTenant,
  useActualizarUsuarioTenant,
} from "@/features/usuarios-tenant/hooks/useUsuariosTenant";
import type { Usuario } from "@/features/usuarios-tenant/types/usuarios";
import { FilterableTable } from "@/shared/components/FilterableTable";
import type { Column } from "@/shared/components/FilterableTable";

export function UsuariosListPage() {
  const [estadoFilter, setEstadoFilter] = useState<string>("");

  const navigate = useNavigate();
  const { data: usuarios = [], isLoading, error } = useUsuariosTenant();
  const actualizarMutation = useActualizarUsuarioTenant();

  const filtered = usuarios.filter((u) => {
    if (estadoFilter && u.estado !== estadoFilter) return false;
    return true;
  });

  const rows = filtered as unknown as Record<string, unknown>[];

  const columns: Column<Record<string, unknown>>[] = [
    {
      key: "nombre",
      label: "Nombre",
      sortable: true,
      render: (row) =>
        `${row.nombre as string} ${(row.apellidos as string) ?? ""}`.trim(),
    },
    {
      key: "email",
      label: "Email",
      sortable: true,
    },
    {
      key: "regional",
      label: "Regional",
      render: (row) => (row.regional as string) ?? "—",
    },
    {
      key: "legajo",
      label: "Legajo",
      render: (row) => (row.legajo as string) ?? "—",
    },
    {
      key: "estado",
      label: "Estado",
      render: (row) =>
        row.estado === "Activo" ? (
          <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-800">
            Activo
          </span>
        ) : (
          <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-700">
            Inactivo
          </span>
        ),
    },
    {
      key: "acciones",
      label: "Acciones",
      render: (row) => {
        const usuario = row as unknown as Usuario;
        const esActivo = usuario.estado === "Activo";
        return (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => navigate(`/usuarios/${usuario.id}/editar`)}
              className="text-xs text-brand-600 underline hover:text-brand-800"
            >
              Editar
            </button>
            <button
              type="button"
              onClick={() =>
                actualizarMutation.mutate({
                  id: usuario.id,
                  payload: { estado: esActivo ? "Inactivo" : "Activo" },
                })
              }
              className="text-xs text-gray-500 underline hover:text-gray-700"
            >
              {esActivo ? "Desactivar" : "Activar"}
            </button>
          </div>
        );
      },
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Usuarios</h1>
          <p className="mt-1 text-sm text-gray-500">Gestión de usuarios del sistema</p>
        </div>
        <button
          type="button"
          onClick={() => navigate("/usuarios/nuevo")}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          Nuevo usuario
        </button>
      </div>

      <FilterableTable
        columns={columns}
        data={rows}
        total={filtered.length}
        isLoading={isLoading}
        error={error?.message ?? null}
        filters={
          <div className="flex flex-wrap items-center gap-3">
            <select
              value={estadoFilter}
              onChange={(e) => setEstadoFilter(e.target.value)}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="">Todos los estados</option>
              <option value="Activo">Activos</option>
              <option value="Inactivo">Inactivos</option>
            </select>

            {estadoFilter && (
              <button
                type="button"
                onClick={() => setEstadoFilter("")}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Limpiar
              </button>
            )}
          </div>
        }
        exportFileName="usuarios.csv"
      />
    </div>
  );
}
