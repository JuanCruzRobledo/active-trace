import type { Liquidacion } from "@/features/liquidaciones/types/liquidaciones";
import type { Column } from "@/shared/components/FilterableTable";
import { FilterableTable } from "@/shared/components/FilterableTable";

interface SegmentoLiquidacionTableProps {
  titulo: string;
  descripcion?: string;
  items: Liquidacion[];
  isLoading?: boolean;
  error?: string | null;
  informativo?: boolean;
  onVerDetalle?: (liq: Liquidacion) => void;
  onCerrar?: (liq: Liquidacion) => void;
}

export function SegmentoLiquidacionTable({
  titulo,
  descripcion,
  items,
  isLoading,
  error,
  informativo = false,
  onVerDetalle,
  onCerrar,
}: SegmentoLiquidacionTableProps) {
  const rows = items as unknown as Record<string, unknown>[];

  const columns: Column<Record<string, unknown>>[] = [
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
      render: (row) => (
        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
          {row.rol as string}
        </span>
      ),
    },
    {
      key: "comisiones",
      label: "Comisiones",
      sortable: true,
    },
    {
      key: "monto_base",
      label: "Base",
      render: (row) => `$${row.monto_base as string}`,
    },
    {
      key: "monto_plus",
      label: "Plus",
      render: (row) => `$${row.monto_plus as string}`,
    },
    {
      key: "total",
      label: "Total",
      sortable: true,
      render: (row) => (
        <span className="font-semibold text-gray-900">
          ${row.total as string}
        </span>
      ),
    },
    {
      key: "estado",
      label: "Estado",
      render: (row) => {
        const estado = row.estado as string;
        const color =
          estado === "cerrada"
            ? "bg-green-100 text-green-800"
            : "bg-yellow-100 text-yellow-800";
        return (
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${color}`}>
            {estado}
          </span>
        );
      },
    },
    {
      key: "acciones",
      label: "Acciones",
      render: (row) => {
        const liq = row as unknown as Liquidacion;
        const cerrada = liq.estado === "cerrada";
        return (
          <div className="flex items-center gap-2">
            {onVerDetalle && (
              <button
                type="button"
                onClick={() => onVerDetalle(liq)}
                className="text-xs text-brand-600 underline hover:text-brand-800"
              >
                Ver detalle
              </button>
            )}
            {onCerrar && !cerrada && !informativo && (
              <button
                type="button"
                onClick={() => onCerrar(liq)}
                className="text-xs text-red-600 underline hover:text-red-800"
              >
                Cerrar
              </button>
            )}
            {cerrada && (
              <span className="text-xs text-gray-400">Cerrada</span>
            )}
          </div>
        );
      },
    },
  ];

  return (
    <section className="space-y-3">
      <div className="flex items-center gap-3">
        <h2 className="text-lg font-semibold text-gray-800">{titulo}</h2>
        {informativo && (
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
            Solo informativo
          </span>
        )}
        <span className="text-sm text-gray-500">({items.length} registros)</span>
      </div>
      {descripcion && (
        <p className="text-sm text-gray-500">{descripcion}</p>
      )}
      <FilterableTable
        columns={columns}
        data={rows}
        total={items.length}
        isLoading={isLoading}
        error={error}
        exportFileName={`${titulo.toLowerCase().replace(/\s+/g, "-")}.csv`}
      />
    </section>
  );
}
