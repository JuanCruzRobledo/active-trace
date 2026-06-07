import { useState } from "react";
import { FilterableTable } from "@/shared/components/FilterableTable";
import {
  useMisTareas,
  useActualizarEstadoTarea,
} from "@/features/tareas/hooks/useTareas";
import type { Tarea } from "@/features/tareas/types/tareas";
import type { Column } from "@/shared/components/FilterableTable";

const estado_colors: Record<string, string> = {
  pendiente: "bg-yellow-100 text-yellow-800",
  en_curso: "bg-blue-100 text-blue-800",
  completada: "bg-green-100 text-green-800",
  cancelada: "bg-gray-100 text-gray-600",
};

export function MisTareasPage() {
  const [estadoFilter, setEstadoFilter] = useState("");
  const { data, isLoading, error } = useMisTareas(estadoFilter || undefined);
  const actualizarEstado = useActualizarEstadoTarea();

  const items = (data?.items ?? []) as unknown as Record<string, unknown>[];

  const columns: Column<Record<string, unknown>>[] = [
    { key: "descripcion", label: "Descripción", sortable: true },
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
                payload: { nuevo_estado: e.target.value as Tarea["estado"] },
              })
            }
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${estado_colors[estado] ?? "bg-gray-100 text-gray-800"} cursor-pointer border-0`}
          >
            <option value="pendiente">Pendiente</option>
            <option value="en_curso">En curso</option>
            <option value="completada">Completada</option>
            <option value="cancelada">Cancelada</option>
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
        <h1 className="text-2xl font-bold text-gray-900">Mis Tareas</h1>
        <p className="mt-1 text-sm text-gray-500">
          Tareas asignadas a vos
        </p>
      </div>

      <FilterableTable
        columns={columns}
        data={items}
        total={data?.total ?? items.length}
        isLoading={isLoading}
        error={error?.message ?? null}
        filters={
          <select
            value={estadoFilter}
            onChange={(e) => setEstadoFilter(e.target.value)}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">Todos los estados</option>
            <option value="pendiente">Pendiente</option>
            <option value="en_curso">En curso</option>
            <option value="completada">Completada</option>
            <option value="cancelada">Cancelada</option>
          </select>
        }
        exportFileName="mis-tareas.csv"
      />
    </div>
  );
}
