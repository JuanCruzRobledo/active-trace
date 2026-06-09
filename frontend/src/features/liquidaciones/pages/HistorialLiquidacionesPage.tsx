import { useState } from "react";
import { useLiquidaciones } from "@/features/liquidaciones/hooks/useLiquidaciones";
import type { Liquidacion } from "@/features/liquidaciones/types/liquidaciones";
import { FilterableTable } from "@/shared/components/FilterableTable";
import { DetalleDocenteDialog } from "@/features/liquidaciones/components/DetalleDocenteDialog";
import type { Column } from "@/shared/components/FilterableTable";

export function HistorialLiquidacionesPage() {
  const [periodo, setPeriodo] = useState<string>("");
  const [detalleLiq, setDetalleLiq] = useState<Liquidacion | null>(null);

  const { data: liquidaciones, isLoading, error } = useLiquidaciones(
    periodo ? { periodo } : undefined,
  );

  const cerradas = (liquidaciones ?? []).filter((l) => l.estado === "cerrada");
  const rows = cerradas as unknown as Record<string, unknown>[];

  const columns: Column<Record<string, unknown>>[] = [
    {
      key: "periodo",
      label: "Período",
      sortable: true,
    },
    {
      key: "usuario_id",
      label: "Docente (ID)",
      render: (row) => (
        <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs">
          {(row.usuario_id as string)?.slice(0, 8)}...
        </code>
      ),
    },
    {
      key: "rol",
      label: "Rol",
      sortable: true,
    },
    {
      key: "comisiones",
      label: "Comisiones",
      sortable: true,
    },
    {
      key: "total",
      label: "Total",
      sortable: true,
      render: (row) => (
        <span className="font-semibold">${row.total as string}</span>
      ),
    },
    {
      key: "cerrada_at",
      label: "Cerrada el",
      sortable: true,
      render: (row) =>
        row.cerrada_at
          ? new Date(row.cerrada_at as string).toLocaleDateString("es-AR")
          : "-",
    },
    {
      key: "acciones",
      label: "Acciones",
      render: (row) => (
        <button
          type="button"
          onClick={() => setDetalleLiq(row as unknown as Liquidacion)}
          className="text-xs text-brand-600 underline hover:text-brand-800"
        >
          Ver detalle
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Historial de Liquidaciones
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Liquidaciones cerradas con acceso a detalle
          </p>
        </div>

        <div className="flex items-center gap-2">
          <label
            htmlFor="hist-periodo"
            className="text-sm font-medium text-gray-700"
          >
            Período
          </label>
          <input
            id="hist-periodo"
            type="month"
            value={periodo}
            onChange={(e) => setPeriodo(e.target.value)}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          {periodo && (
            <button
              type="button"
              onClick={() => setPeriodo("")}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Limpiar
            </button>
          )}
        </div>
      </div>

      <FilterableTable
        columns={columns}
        data={rows}
        total={cerradas.length}
        isLoading={isLoading}
        error={error?.message ?? null}
        exportFileName="historial-liquidaciones.csv"
      />

      <DetalleDocenteDialog
        liquidacion={detalleLiq}
        onClose={() => setDetalleLiq(null)}
      />
    </div>
  );
}
