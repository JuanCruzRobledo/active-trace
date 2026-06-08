import { useState } from "react";
import {
  useAccionesPorDia,
  useComunicacionesPorDocente,
  useInteraccionesPorDocenteMateria,
  useUltimasAcciones,
} from "@/features/auditoria/hooks/useAuditoria";
import type { AuditoriaFilters } from "@/features/auditoria/types/auditoria";
import { AccionesPorDiaChart } from "@/features/auditoria/components/AccionesPorDiaChart";
import { ComunicacionesPorDocentePanel } from "@/features/auditoria/components/ComunicacionesPorDocentePanel";
import { InteraccionesPanel } from "@/features/auditoria/components/InteraccionesPanel";

export function AuditoriaPanelPage() {
  const [filters, setFilters] = useState<AuditoriaFilters>({});

  const { data: acciones = [], isLoading: loadingA, error: errorA } =
    useAccionesPorDia(filters);
  const { data: comunicaciones = [], isLoading: loadingC, error: errorC } =
    useComunicacionesPorDocente(filters);
  const { data: interacciones = [], isLoading: loadingI, error: errorI } =
    useInteraccionesPorDocenteMateria(filters);
  const { data: ultimas = [], isLoading: loadingU, error: errorU } =
    useUltimasAcciones(10);

  const handleFilterChange = (key: keyof AuditoriaFilters, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value || undefined }));
  };

  return (
    <div className="space-y-8">
      {/* Header + Filtros */}
      <div className="space-y-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Panel de Auditoría
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Métricas y estadísticas de uso del sistema
          </p>
        </div>

        {/* Filtros */}
        <div className="flex flex-wrap items-end gap-4 rounded-lg border bg-white p-4 shadow-sm">
          <div>
            <label
              htmlFor="audit-desde"
              className="block text-sm font-medium text-gray-700"
            >
              Desde
            </label>
            <input
              id="audit-desde"
              type="date"
              value={filters.fecha_desde ?? ""}
              onChange={(e) => handleFilterChange("fecha_desde", e.target.value)}
              className="mt-1 block rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          <div>
            <label
              htmlFor="audit-hasta"
              className="block text-sm font-medium text-gray-700"
            >
              Hasta
            </label>
            <input
              id="audit-hasta"
              type="date"
              value={filters.fecha_hasta ?? ""}
              onChange={(e) => handleFilterChange("fecha_hasta", e.target.value)}
              className="mt-1 block rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          {(filters.fecha_desde || filters.fecha_hasta || filters.materia_id) && (
            <button
              type="button"
              onClick={() => setFilters({})}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Limpiar filtros
            </button>
          )}
        </div>
      </div>

      {/* Grid de sub-paneles */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Acciones por Día */}
        <section className="space-y-3 rounded-lg border bg-white p-4 shadow-sm">
          <h2 className="text-base font-semibold text-gray-800">
            Acciones por Día
          </h2>
          <AccionesPorDiaChart
            data={acciones}
            isLoading={loadingA}
            error={errorA?.message ?? null}
          />
        </section>

        {/* Comunicaciones por Docente */}
        <section className="space-y-3 rounded-lg border bg-white p-4 shadow-sm">
          <h2 className="text-base font-semibold text-gray-800">
            Comunicaciones por Docente
          </h2>
          <ComunicacionesPorDocentePanel
            data={comunicaciones}
            isLoading={loadingC}
            error={errorC?.message ?? null}
          />
        </section>

        {/* Interacciones por Docente-Materia */}
        <section className="col-span-1 space-y-3 rounded-lg border bg-white p-4 shadow-sm lg:col-span-2">
          <h2 className="text-base font-semibold text-gray-800">
            Interacciones por Docente-Materia
          </h2>
          <InteraccionesPanel
            data={interacciones}
            isLoading={loadingI}
            error={errorI?.message ?? null}
          />
        </section>

        {/* Últimas Acciones */}
        <section className="col-span-1 space-y-3 rounded-lg border bg-white p-4 shadow-sm lg:col-span-2">
          <h2 className="text-base font-semibold text-gray-800">
            Últimas Acciones
          </h2>
          {loadingU ? (
            <p className="text-sm text-gray-400">Cargando...</p>
          ) : errorU ? (
            <p className="text-sm text-red-600">{errorU.message}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                      Fecha
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                      Acción
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                      Registros
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                      IP
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {ultimas.length === 0 && (
                    <tr>
                      <td
                        colSpan={4}
                        className="px-4 py-4 text-center text-gray-400"
                      >
                        Sin acciones recientes
                      </td>
                    </tr>
                  )}
                  {ultimas.map((u) => (
                    <tr key={u.id} className="hover:bg-gray-50">
                      <td className="px-4 py-2 text-xs text-gray-500">
                        {u.created_at
                          ? new Date(u.created_at).toLocaleString("es-AR")
                          : "—"}
                      </td>
                      <td className="px-4 py-2 font-mono text-xs text-gray-900">
                        {u.accion}
                      </td>
                      <td className="px-4 py-2 text-gray-700">
                        {u.registros ?? "—"}
                      </td>
                      <td className="px-4 py-2 text-xs text-gray-500">
                        {u.ip ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
