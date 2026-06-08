import type { KpisLiquidacion } from "@/features/liquidaciones/types/liquidaciones";

interface LiquidacionKpiHeaderProps {
  kpis: KpisLiquidacion;
}

function formatMonto(value: number): string {
  return value.toLocaleString("es-AR", {
    style: "currency",
    currency: "ARS",
    minimumFractionDigits: 2,
  });
}

export function LiquidacionKpiHeader({ kpis }: LiquidacionKpiHeaderProps) {
  return (
    <div
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
      aria-label="KPIs de liquidación"
    >
      <div className="rounded-lg border bg-white p-4 shadow-sm">
        <p className="text-xs font-medium uppercase tracking-wider text-gray-500">
          Total sin factura
        </p>
        <p
          className="mt-1 text-2xl font-bold text-gray-900"
          data-testid="kpi-total-sin-factura"
        >
          {formatMonto(kpis.totalSinFactura)}
        </p>
        <p className="mt-1 text-xs text-gray-400">General + NEXO</p>
      </div>

      <div className="rounded-lg border bg-white p-4 shadow-sm">
        <p className="text-xs font-medium uppercase tracking-wider text-gray-500">
          Total general
        </p>
        <p
          className="mt-1 text-2xl font-bold text-blue-700"
          data-testid="kpi-total-general"
        >
          {formatMonto(kpis.totalGeneral)}
        </p>
      </div>

      <div className="rounded-lg border bg-white p-4 shadow-sm">
        <p className="text-xs font-medium uppercase tracking-wider text-gray-500">
          Total NEXO
        </p>
        <p
          className="mt-1 text-2xl font-bold text-purple-700"
          data-testid="kpi-total-nexo"
        >
          {formatMonto(kpis.totalNexo)}
        </p>
      </div>

      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 shadow-sm">
        <p className="text-xs font-medium uppercase tracking-wider text-amber-700">
          Docentes facturadores
        </p>
        <p
          className="mt-1 text-2xl font-bold text-amber-700"
          data-testid="kpi-total-facturan"
        >
          {formatMonto(kpis.totalFacturan)}
        </p>
        <p className="mt-1 text-xs text-amber-600">
          Informativo — no sumado al total
        </p>
      </div>
    </div>
  );
}
