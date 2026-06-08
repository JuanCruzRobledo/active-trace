import { useState } from "react";
import { useLog } from "@/features/auditoria/hooks/useAuditoria";
import type { LogFilters } from "@/features/auditoria/types/auditoria";
import { FilterableTable } from "@/shared/components/FilterableTable";
import type { Column } from "@/shared/components/FilterableTable";

export function LogAuditoriaPage() {
  const [filters, setFilters] = useState<LogFilters>({});

  const { data, isLoading, error } = useLog({ ...filters, limit: 50 });

  const items = data?.items ?? [];
  const rows = items as unknown as Record<string, unknown>[];

  const columns: Column<Record<string, unknown>>[] = [
    {
      key: "created_at",
      label: "Fecha/Hora",
      sortable: true,
      render: (row) =>
        row.created_at
          ? new Date(row.created_at as string).toLocaleString("es-AR")
          : "—",
    },
    {
      key: "usuario_id",
      label: "Usuario (ID)",
      render: (row) =>
        row.usuario_id ? (
          <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs">
            {(row.usuario_id as string).slice(0, 8)}...
          </code>
        ) : (
          "—"
        ),
    },
    {
      key: "materia_id",
      label: "Materia (ID)",
      render: (row) =>
        row.materia_id ? (
          <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs">
            {(row.materia_id as string).slice(0, 8)}...
          </code>
        ) : (
          "—"
        ),
    },
    {
      key: "accion",
      label: "Acción",
      sortable: true,
      render: (row) => (
        <span className="font-mono text-xs text-gray-900">
          {row.accion as string}
        </span>
      ),
    },
    {
      key: "registros",
      label: "Registros",
      render: (row) => (row.registros as number) ?? "—",
    },
    {
      key: "ip",
      label: "IP",
      render: (row) => (
        <span className="font-mono text-xs text-gray-500">
          {(row.ip as string) ?? "—"}
        </span>
      ),
    },
    {
      key: "user_agent",
      label: "User Agent",
      render: (row) => (
        <span
          className="max-w-xs truncate block text-xs text-gray-400"
          title={(row.user_agent as string) ?? ""}
        >
          {(row.user_agent as string) ?? "—"}
        </span>
      ),
    },
  ];

  const handleFilterChange = (key: keyof LogFilters, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value || undefined }));
  };

  const hasFilters = Object.keys(filters).some(
    (k) => k !== "limit" && filters[k as keyof LogFilters] !== undefined,
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Log de Auditoría</h1>
        <p className="mt-1 text-sm text-gray-500">
          Registro completo de acciones del sistema
        </p>
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap items-end gap-4 rounded-lg border bg-white p-4 shadow-sm">
        <div>
          <label
            htmlFor="log-desde"
            className="block text-sm font-medium text-gray-700"
          >
            Desde
          </label>
          <input
            id="log-desde"
            type="date"
            value={filters.fecha_desde ?? ""}
            onChange={(e) => handleFilterChange("fecha_desde", e.target.value)}
            className="mt-1 block rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        <div>
          <label
            htmlFor="log-hasta"
            className="block text-sm font-medium text-gray-700"
          >
            Hasta
          </label>
          <input
            id="log-hasta"
            type="date"
            value={filters.fecha_hasta ?? ""}
            onChange={(e) => handleFilterChange("fecha_hasta", e.target.value)}
            className="mt-1 block rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        <div>
          <label
            htmlFor="log-accion"
            className="block text-sm font-medium text-gray-700"
          >
            Acción
          </label>
          <input
            id="log-accion"
            type="text"
            value={filters.accion ?? ""}
            onChange={(e) => handleFilterChange("accion", e.target.value)}
            placeholder="importar_notas..."
            className="mt-1 block rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

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

      <FilterableTable
        columns={columns}
        data={rows}
        total={data?.total ?? items.length}
        isLoading={isLoading}
        error={error?.message ?? null}
        exportFileName="log-auditoria.csv"
      />
    </div>
  );
}
