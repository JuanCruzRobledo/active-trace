import { useState } from "react";
import { FilterableTable } from "@/shared/components/FilterableTable";
import { Input } from "@/shared/components/Input";
import { useInstancias } from "@/features/encuentros/hooks/useEncuentros";
import type { InstanciasFilters } from "@/features/encuentros/types/encuentros";
import type { Column } from "@/shared/components/FilterableTable";

const estado_styles: Record<string, string> = {
  realizado: "bg-green-100 text-green-800 ring-green-600",
  pendiente: "bg-yellow-100 text-yellow-800 ring-yellow-600",
  cancelado: "bg-red-100 text-red-800 ring-red-600",
};

const estado_labels: Record<string, string> = {
  realizado: "Realizado",
  pendiente: "Pendiente",
  cancelado: "Cancelado",
};

export function EncuentrosAdminPage() {
  const [filters, setFilters] = useState<InstanciasFilters>({});
  const { data, isLoading, error } = useInstancias(filters);

  const items = (data?.items ?? []) as unknown as Record<string, unknown>[];
  const hasFilters = Object.values(filters).some((v) => v !== undefined);

  const columns: Column<Record<string, unknown>>[] = [
    {
      key: "fecha",
      label: "Fecha",
      sortable: true,
      render: (row) => {
        const d = row.fecha as string;
        return d ? new Date(d).toLocaleDateString() : "-";
      },
    },
    {
      key: "hora_inicio",
      label: "Inicio",
      render: (row) => (row.hora_inicio as string) ?? "-",
    },
    {
      key: "hora_fin",
      label: "Fin",
      render: (row) => (row.hora_fin as string) ?? "-",
    },
    {
      key: "estado",
      label: "Estado",
      sortable: true,
      render: (row) => {
        const est = (row.estado as string) ?? "pendiente";
        return (
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${estado_styles[est] ?? "bg-gray-100 text-gray-800"}`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                est === "realizado"
                  ? "bg-green-500"
                  : est === "cancelado"
                    ? "bg-red-500"
                    : "bg-yellow-500"
              }`}
            />
            {estado_labels[est] ?? est}
          </span>
        );
      },
    },
    {
      key: "created_at",
      label: "Creado",
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
        <h1 className="text-2xl font-bold text-gray-900">Encuentros</h1>
        <p className="mt-1 text-sm text-gray-500">
          Administración de instancias de encuentros
        </p>
      </div>

      <FilterableTable
        columns={columns}
        data={items}
        total={data?.total ?? items.length}
        isLoading={isLoading}
        error={error?.message ?? null}
        filters={
          <div className="flex flex-wrap items-center gap-3">
            <div className="w-36">
              <Input
                type="date"
                value={filters.desde ?? ""}
                onChange={(e) =>
                  setFilters((prev) => ({
                    ...prev,
                    desde: e.target.value || undefined,
                  }))
                }
                placeholder="Desde"
              />
            </div>
            <div className="w-36">
              <Input
                type="date"
                value={filters.hasta ?? ""}
                onChange={(e) =>
                  setFilters((prev) => ({
                    ...prev,
                    hasta: e.target.value || undefined,
                  }))
                }
                placeholder="Hasta"
              />
            </div>
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
              <option value="">Todos</option>
              <option value="pendiente">Pendiente</option>
              <option value="realizado">Realizado</option>
              <option value="cancelado">Cancelado</option>
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
        exportFileName="encuentros.csv"
      />
    </div>
  );
}
