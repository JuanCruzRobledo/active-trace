import { useState } from "react";
import { FilterableTable } from "@/shared/components/FilterableTable";
import {
  useTareasAdmin,
  useActualizarEstadoTarea,
} from "@/features/tareas/hooks/useTareas";
import type { TareasFilters } from "@/features/tareas/types/tareas";
import type { Column } from "@/shared/components/FilterableTable";

const estado_colors: Record<string, string> = {
  pendiente: "bg-yellow-100 text-yellow-800",
  en_curso: "bg-blue-100 text-blue-800",
  completada: "bg-green-100 text-green-800",
  cancelada: "bg-gray-100 text-gray-600",
};

const estado_labels: Record<string, string> = {
  pendiente: "Pendiente",
  en_curso: "En curso",
  completada: "Completada",
  cancelada: "Cancelada",
};

export function TareasAdminPage() {
  const [filters, setFilters] = useState<TareasFilters>({});
  const { data, isLoading, error } = useTareasAdmin(filters);
  const actualizarEstado = useActualizarEstadoTarea();

  const items = (data?.items ?? []) as unknown as Record<string, unknown>[];
  const hasFilters = Object.values(filters).some((v) => v !== undefined);

  const columns: Column<Record<string, unknown>>[] = [
    {
      key: "descripcion",
      label: "Descripción",
      sortable: true,
      render: (row) => (
        <span className="max-w-xs truncate block">
          {(row.descripcion as string) ?? "-"}
        </span>
      ),
    },
    {
      key: "asignado_a",
      label: "Asignado a",
      render: (row) => (
        <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs">
          {(row.asignado_a as string)?.slice(0, 8)}...
        </code>
      ),
    },
    {
      key: "asignado_por",
      label: "Asignado por",
      render: (row) => (
        <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs">
          {(row.asignado_por as string)?.slice(0, 8)}...
        </code>
      ),
    },
    {
      key: "estado",
      label: "Estado",
      sortable: true,
      render: (row) => {
        const estado = row.estado as string;
        return (
          <select
            value={estado}
            onChange={(e) =>
              actualizarEstado.mutate({
                id: row.id as string,
                payload: { nuevo_estado: e.target.value as any },
              })
            }
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${estado_colors[estado] ?? "bg-gray-100 text-gray-800"} cursor-pointer border-0`}
          >
            {Object.entries(estado_labels).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        );
      },
    },
    {
      key: "created_at",
      label: "Creada",
      sortable: true,
      render: (row) =>
        row.created_at
          ? new Date(row.created_at as string).toLocaleDateString()
          : "-",
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Administración de Tareas
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Gestioná todas las tareas del sistema
        </p>
      </div>

      <FilterableTable
        columns={columns}
        data={items}
        total={data?.total ?? items.length}
        isLoading={isLoading}
        error={error?.message ?? null}
        onSearch={(q) =>
          setFilters((prev) => ({ ...prev, busqueda: q || undefined }))
        }
        filters={
          <div className="flex flex-wrap items-center gap-3">
            <select
              value={filters.estado ?? ""}
              onChange={(e) =>
                setFilters((prev) => ({
                  ...prev,
                  estado: e.target.value || undefined,
                }))
              }
              className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="">Todos los estados</option>
              <option value="pendiente">Pendiente</option>
              <option value="en_curso">En curso</option>
              <option value="completada">Completada</option>
              <option value="cancelada">Cancelada</option>
            </select>
            {hasFilters && (
              <button
                type="button"
                onClick={() => setFilters({})}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Limpiar
              </button>
            )}
          </div>
        }
        exportFileName="tareas-admin.csv"
      />
    </div>
  );
}
