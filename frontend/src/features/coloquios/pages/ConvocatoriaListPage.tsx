import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FilterableTable } from "@/shared/components/FilterableTable";
import { Button } from "@/shared/components/Button";
import {
  useConvocatorias,
  useCerrarConvocatoria,
} from "@/features/coloquios/hooks/useColoquios";
import type { ConvocatoriasFilters } from "@/features/coloquios/types/coloquios";
import type { Column } from "@/shared/components/FilterableTable";

const estado_colors: Record<string, string> = {
  abierta: "bg-green-100 text-green-800",
  cerrada: "bg-gray-100 text-gray-600",
  en_curso: "bg-blue-100 text-blue-800",
};

export function ConvocatoriaListPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<ConvocatoriasFilters>({});
  const { data, isLoading, error } = useConvocatorias(filters);
  const cerrar = useCerrarConvocatoria();

  const items = (data?.items ?? []) as unknown as Record<string, unknown>[];

  const columns: Column<Record<string, unknown>>[] = [
    { key: "instancia", label: "Convocatoria", sortable: true },
    {
      key: "estado",
      label: "Estado",
      sortable: true,
      render: (row) => {
        const est = (row.estado as string) ?? "abierta";
        return (
          <span
            className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${estado_colors[est] ?? "bg-gray-100 text-gray-800"}`}
          >
            {est}
          </span>
        );
      },
    },
    {
      key: "cupos_por_dia",
      label: "Cupos/día",
      render: (row) => (row.cupos_por_dia as number) ?? "-",
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
    {
      key: "acciones",
      label: "Acciones",
      render: (row) => (
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="ghost"
            onClick={() => navigate(`/coloquios/convocatorias/${row.id}/editar`)}
          >
            Editar
          </Button>
          {(row.estado as string) === "abierta" && (
            <Button
              type="button"
              variant="danger"
              onClick={() => cerrar.mutate(row.id as string)}
              is_loading={cerrar.isPending}
            >
              Cerrar
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Convocatorias</h1>
          <p className="mt-1 text-sm text-gray-500">
            Gestioná las convocatorias de coloquio
          </p>
        </div>
        <Button onClick={() => navigate("/coloquios/convocatorias/nueva")}>
          Nueva Convocatoria
        </Button>
      </div>

      <FilterableTable
        columns={columns}
        data={items}
        total={data?.total ?? items.length}
        isLoading={isLoading}
        error={error?.message ?? null}
        filters={
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
            <option value="abierta">Abierta</option>
            <option value="en_curso">En curso</option>
            <option value="cerrada">Cerrada</option>
          </select>
        }
        exportFileName="convocatorias.csv"
      />
    </div>
  );
}
