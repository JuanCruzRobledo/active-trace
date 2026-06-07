import { useState } from "react";
import { Input } from "@/shared/components/Input";
import { ErrorMessage } from "@/shared/components/ErrorMessage";
import { ContextoAcademicoSelector } from "@/shared/components/ContextoAcademicoSelector";
import { FilterableTable, type Column } from "@/shared/components/FilterableTable";
import { useMonitorGeneral } from "@/features/monitores/hooks/useMonitorGeneral";
import type { MonitorGeneralFilters } from "@/features/monitores/types/monitores";
import type { AlumnoGeneralRow } from "@/features/monitores/types/monitores";

const estado_badge: Record<string, string> = {
  al_dia: "bg-green-100 text-green-800",
  en_seguimiento: "bg-yellow-100 text-yellow-800",
  critico: "bg-red-100 text-red-800",
};

const estado_label: Record<string, string> = {
  al_dia: "Al día",
  en_seguimiento: "En seguimiento",
  critico: "Crítico",
};

export function GeneralView() {
  const [filters, set_filters] = useState<MonitorGeneralFilters>({});
  const { data, isLoading, isError, error } = useMonitorGeneral(filters);

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  const update_filter = (key: keyof MonitorGeneralFilters, value: string | undefined) => {
    set_filters((prev) => ({ ...prev, [key]: value || undefined }));
  };

  const columns: Column<AlumnoGeneralRow>[] = [
    { key: "alumno", label: "Alumno", sortable: true },
    { key: "correo", label: "Correo" },
    { key: "comision", label: "Comisión" },
    { key: "materia", label: "Materia" },
    { key: "total_actividades", label: "Total Act.", sortable: true },
    { key: "aprobadas", label: "Aprobadas", sortable: true },
    { key: "pendientes", label: "Pendientes", sortable: true },
    { key: "ultima_actividad", label: "Última Actividad" },
    {
      key: "estado_general",
      label: "Estado General",
      sortable: true,
      render: (row) => (
        <span
          className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
            estado_badge[row.estado_general] ?? "bg-gray-100 text-gray-800"
          }`}
        >
          {estado_label[row.estado_general] ?? row.estado_general}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Monitor General</h1>
        <p className="mt-1 text-sm text-gray-500">
          Estado general de actividades por alumno
        </p>
      </div>

      <div className="rounded-lg border bg-white p-4 shadow-sm">
        <div className="space-y-3">
          <ContextoAcademicoSelector
            onChange={(ctx) => update_filter("materia_id", ctx.materiaId)}
          />
          <div className="flex flex-wrap gap-3">
            <div className="w-44">
              <label className="mb-1 block text-xs font-medium text-gray-600">
                Regional
              </label>
              <Input
                placeholder="Regional"
                value={filters.regional ?? ""}
                onChange={(e) => update_filter("regional", e.target.value)}
              />
            </div>
            <div className="w-36">
              <label className="mb-1 block text-xs font-medium text-gray-600">
                Comisión
              </label>
              <Input
                placeholder="Comisión"
                value={filters.comision ?? ""}
                onChange={(e) => update_filter("comision", e.target.value)}
              />
            </div>
          </div>
        </div>
      </div>

      {isError && (
        <ErrorMessage
          message={error?.message ?? "Error al cargar el monitor general."}
        />
      )}

      <FilterableTable<AlumnoGeneralRow>
        columns={columns}
        data={items}
        total={total}
        isLoading={isLoading}
        error={isError ? (error?.message ?? "Error") : null}
        onSearch={(q) => update_filter("q", q || undefined)}
        exportFileName="monitor-general.csv"
      />

      {!isLoading && !isError && total === 0 && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center">
          <p className="text-lg font-medium text-gray-700">
            No se encontraron resultados
          </p>
          <p className="mt-1 text-sm text-gray-500">
            Ajustá los filtros o seleccioná una materia para ver datos.
          </p>
        </div>
      )}
    </div>
  );
}
