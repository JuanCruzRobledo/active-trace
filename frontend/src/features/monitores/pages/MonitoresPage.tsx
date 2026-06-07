import { useState } from "react";
import { Input } from "@/shared/components/Input";
import { Button } from "@/shared/components/Button";
import { LoadingSpinner } from "@/shared/components/LoadingSpinner";
import { ErrorMessage } from "@/shared/components/ErrorMessage";
import { useMonitorSeguimiento } from "@/features/monitores/hooks/useMonitorSeguimiento";
import { exportarMonitores } from "@/features/monitores/services/seguimiento";
import type { MonitoresFilters } from "@/features/monitores/services/seguimiento";

const defaultFilters: MonitoresFilters = {};

export function MonitoresPage() {
  const [filters, setFilters] = useState<MonitoresFilters>({ ...defaultFilters });
  const { data, isLoading, isError, error } = useMonitorSeguimiento(filters);

  const hasFilters =
    filters.nombre ||
    filters.correo ||
    filters.comision ||
    filters.materia ||
    filters.actividad ||
    filters.actividades_min !== undefined;

  const items = data?.items ?? [];
  const isEmpty = !isLoading && !isError && items.length === 0;

  const handleExport = async () => {
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

  const handleClearFilters = () => {
    setFilters({ ...defaultFilters });
  };

  const updateFilter = (key: keyof MonitoresFilters, value: string | undefined) => {
    setFilters((prev) => ({ ...prev, [key]: value || undefined }));
  };

  return (
    <div className="space-y-6">
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
          {hasFilters && (
            <Button variant="ghost" onClick={handleClearFilters}>
              Limpiar filtros
            </Button>
          )}
          <Button variant="secondary" onClick={handleExport}>
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
            onChange={(e) => updateFilter("nombre", e.target.value)}
          />
        </div>
        <div className="w-44">
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Correo
          </label>
          <Input
            placeholder="Filtrar por correo"
            value={filters.correo ?? ""}
            onChange={(e) => updateFilter("correo", e.target.value)}
          />
        </div>
        <div className="w-36">
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Comisión
          </label>
          <Input
            placeholder="Comisión"
            value={filters.comision ?? ""}
            onChange={(e) => updateFilter("comision", e.target.value)}
          />
        </div>
        <div className="w-40">
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Materia
          </label>
          <Input
            placeholder="Materia"
            value={filters.materia ?? ""}
            onChange={(e) => updateFilter("materia", e.target.value)}
          />
        </div>
        <div className="w-40">
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Actividad
          </label>
          <Input
            placeholder="Actividad"
            value={filters.actividad ?? ""}
            onChange={(e) => updateFilter("actividad", e.target.value)}
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
              updateFilter(
                "actividades_min",
                e.target.value ? String(Number(e.target.value)) : undefined,
              )
            }
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

      {isEmpty && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center">
          <p className="text-lg font-medium text-gray-700">
            No tienes alumnos asignados actualmente
          </p>
          <p className="mt-1 text-sm text-gray-500">
            Los datos aparecerán aquí cuando tengas alumnos asignados a tu
            cargo.
          </p>
        </div>
      )}

      {!isLoading && !isError && items.length > 0 && (
        <div className="overflow-x-auto rounded-lg border bg-white shadow-sm">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">
                  Alumno
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">
                  Correo
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">
                  Comisión
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">
                  Materia
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">
                  Actividad
                </th>
                <th className="px-4 py-3 text-center font-medium text-gray-500">
                  Estado
                </th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">
                  Nota
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((row, i) => (
                <tr key={`${row.alumno_id}-${i}`} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {row.alumno}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{row.correo}</td>
                  <td className="px-4 py-3 text-gray-500">{row.comision}</td>
                  <td className="px-4 py-3 text-gray-500">{row.materia}</td>
                  <td className="px-4 py-3 text-gray-500">{row.actividad}</td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                        row.estado === "aprobada"
                          ? "bg-green-100 text-green-800"
                          : row.estado === "pendiente"
                            ? "bg-yellow-100 text-yellow-800"
                            : "bg-gray-100 text-gray-800"
                      }`}
                    >
                      {row.estado}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {row.nota ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="border-t bg-gray-50 px-4 py-2 text-sm text-gray-500">
            {data?.total ?? items.length} registro(s)
          </div>
        </div>
      )}
    </div>
  );
}
