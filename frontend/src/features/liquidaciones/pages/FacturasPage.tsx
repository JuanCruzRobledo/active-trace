import { useState } from "react";
import {
  useFacturas,
  useAbonarFactura,
} from "@/features/liquidaciones/hooks/useLiquidaciones";
import type { Factura } from "@/features/liquidaciones/types/liquidaciones";
import { FilterableTable } from "@/shared/components/FilterableTable";
import { ConfirmDialog } from "@/shared/components/ConfirmDialog";
import type { Column } from "@/shared/components/FilterableTable";

export function FacturasPage() {
  const [estadoFilter, setEstadoFilter] = useState<string>("");
  const [abonarTarget, setAbonarTarget] = useState<Factura | null>(null);

  const { data: facturas = [], isLoading, error } = useFacturas();
  const abonarMutation = useAbonarFactura();

  const filtered =
    estadoFilter
      ? facturas.filter((f) => f.estado === estadoFilter)
      : facturas;

  const rows = filtered as unknown as Record<string, unknown>[];

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
      key: "periodo",
      label: "Período",
      sortable: true,
    },
    {
      key: "detalle",
      label: "Detalle",
      render: (row) => (row.detalle as string) ?? "—",
    },
    {
      key: "referencia_archivo",
      label: "Archivo",
      render: (row) =>
        row.referencia_archivo ? (
          <span className="text-xs text-gray-600">
            {row.referencia_archivo as string}
          </span>
        ) : (
          "—"
        ),
    },
    {
      key: "estado",
      label: "Estado",
      sortable: true,
      render: (row) => {
        const estado = row.estado as string;
        const color =
          estado === "abonada"
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
      key: "cargada_at",
      label: "Cargada",
      sortable: true,
      render: (row) =>
        row.cargada_at
          ? new Date(row.cargada_at as string).toLocaleDateString("es-AR")
          : "—",
    },
    {
      key: "abonada_at",
      label: "Abonada",
      render: (row) =>
        row.abonada_at
          ? new Date(row.abonada_at as string).toLocaleDateString("es-AR")
          : "—",
    },
    {
      key: "acciones",
      label: "Acciones",
      render: (row) => {
        const factura = row as unknown as Factura;
        if (factura.estado === "abonada") return null;
        return (
          <button
            type="button"
            onClick={() => setAbonarTarget(factura)}
            className="text-xs text-brand-600 underline hover:text-brand-800"
          >
            Marcar abonada
          </button>
        );
      },
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Facturas</h1>
        <p className="mt-1 text-sm text-gray-500">
          Gestión de facturas de docentes
        </p>
      </div>

      <FilterableTable
        columns={columns}
        data={rows}
        total={filtered.length}
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
            <option value="abonada">Abonada</option>
          </select>
        }
        exportFileName="facturas.csv"
      />

      <ConfirmDialog
        isOpen={abonarTarget !== null}
        title="Confirmar pago de factura"
        message={`¿Marcar como abonada la factura del docente ${abonarTarget?.usuario_id?.slice(0, 8)}...?`}
        confirmLabel="Sí, marcar abonada"
        cancelLabel="Cancelar"
        variant="info"
        onConfirm={() => {
          if (abonarTarget) {
            abonarMutation.mutate(abonarTarget.id);
            setAbonarTarget(null);
          }
        }}
        onCancel={() => setAbonarTarget(null)}
      />
    </div>
  );
}
