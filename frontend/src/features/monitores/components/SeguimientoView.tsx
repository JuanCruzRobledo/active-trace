import { useState } from "react";
import { Input } from "@/shared/components/Input";
import { Button } from "@/shared/components/Button";
import { LoadingSpinner } from "@/shared/components/LoadingSpinner";
import { ErrorMessage } from "@/shared/components/ErrorMessage";
import { useMonitorSeguimiento } from "@/features/monitores/hooks/useMonitorSeguimiento";
import { exportarMonitores } from "@/features/monitores/services/seguimiento";
import type { MonitoresFilters } from "@/features/monitores/services/seguimiento";
import { SeguimientoTable } from "@/features/monitores/components/SeguimientoTable";

const defaultFilters: MonitoresFilters = {};

export function SeguimientoView() {
  const [filters, set_filters] = useState<MonitoresFilters>({ ...defaultFilters });
  const { data, isLoading, isError, error } = useMonitorSeguimiento(filters);

  const has_filters =
    filters.nombre ||
    filters.correo ||
    filters.comision ||
    filters.materia ||
    filters.actividad ||
    filters.actividades_min !== undefined ||
    filters.fecha_desde ||
    filters.fecha_hasta;

  const items = data?.items ?? [];
  const is_empty = !isLoading && !isError && items.length === 0;

  const handle_export = async () => {
    try {
      const blob = await exportarMonitores(filters);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "monitores-seguimiento.csv";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // handled by error display
    }
  };

  const handle_clear_filters = () => {
    set_filters({ ...defaultFilters });
  };

  const update_filter = (key: keyof MonitoresFilters, value: string | undefined) => {
    set_filters((prev) => ({ ...prev, [key]: value || undefined }));
  };

  return (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Monitor de seguimiento
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Estado de actividades de los alumnos asignados
          </p>
        </div>
        <div className="flex gap-2">
          {has_filters && (
            <Button variant="ghost" onClick={handle_clear_filters}>
              Limpiar filtros
            </Button>
          )}
          <Button variant="secondary" onClick={handle_export}>
            Exportar
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-3 rounded-lg border bg-white p-4 shadow-sm">
        <div className="w-44">
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Nombre
          </label>
          <Input
            placeholder="Filtrar por nombre"
            value={filters.nombre ?? ""}
            onChange={(e) => update_filter("nombre", e.target.value)}
          />
        </div>
        <div className="w-44">
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Correo
          </label>
          <Input
            placeholder="Filtrar por correo"
            value={filters.correo ?? ""}
            onChange={(e) => update_filter("correo", e.target.value)}
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
        <div className="w-40">
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Materia
          </label>
          <Input
            placeholder="Materia"
            value={filters.materia ?? ""}
            onChange={(e) => update_filter("materia", e.target.value)}
          />
        </div>
        <div className="w-40">
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Actividad
          </label>
          <Input
            placeholder="Actividad"
            value={filters.actividad ?? ""}
            onChange={(e) => update_filter("actividad", e.target.value)}
          />
        </div>
        <div className="w-36">
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Act. mínimas
          </label>
          <Input
            type="number"
            min={0}
            placeholder="0"
            value={filters.actividades_min ?? ""}
            onChange={(e) =>
              update_filter(
                "actividades_min",
                e.target.value ? String(Number(e.target.value)) : undefined,
              )
            }
          />
        </div>
        <div className="w-40">
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Desde
          </label>
          <Input
            type="date"
            value={filters.fecha_desde ?? ""}
            onChange={(e) => update_filter("fecha_desde", e.target.value || undefined)}
          />
        </div>
        <div className="w-40">
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Hasta
          </label>
          <Input
            type="date"
            value={filters.fecha_hasta ?? ""}
            onChange={(e) => update_filter("fecha_hasta", e.target.value || undefined)}
          />
        </div>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="h-8 w-8" />
        </div>
      )}

      {isError && (
        <ErrorMessage
          message={error?.message ?? "Error al cargar los datos del monitor."}
        />
      )}

      {is_empty && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center">
          <p className="text-lg font-medium text-gray-700">
            No tienes alumnos asignados actualmente
          </p>
          <p className="mt-1 text-sm text-gray-500">
            Los datos aparecerán aquí cuando tengas alumnos asignados a tu cargo.
          </p>
        </div>
      )}

      {!isLoading && !isError && items.length > 0 && (
        <SeguimientoTable items={items} total={data?.total ?? items.length} />
      )}
    </>
  );
}
