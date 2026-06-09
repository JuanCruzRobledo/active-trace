import { useState } from "react";
import {
  useLiquidaciones,
  useCerrarLiquidacion,
} from "@/features/liquidaciones/hooks/useLiquidaciones";
import type {
  Liquidacion,
  KpisLiquidacion,
  SegmentosLiquidacion,
} from "@/features/liquidaciones/types/liquidaciones";
import { LiquidacionKpiHeader } from "@/features/liquidaciones/components/LiquidacionKpiHeader";
import { SegmentoLiquidacionTable } from "@/features/liquidaciones/components/SegmentoLiquidacionTable";
import { DetalleDocenteDialog } from "@/features/liquidaciones/components/DetalleDocenteDialog";
import { ConfirmDialog } from "@/shared/components/ConfirmDialog";
import { LoadingSpinner } from "@/shared/components/LoadingSpinner";

function buildSegmentos(items: Liquidacion[]): SegmentosLiquidacion {
  return {
    general: items.filter(
      (l) => !l.es_nexo && !l.excluido_por_factura,
    ),
    nexo: items.filter(
      (l) => l.es_nexo && !l.excluido_por_factura,
    ),
    facturan: items.filter((l) => l.excluido_por_factura),
  };
}

function buildKpis(segmentos: SegmentosLiquidacion): KpisLiquidacion {
  const sum = (list: Liquidacion[]) =>
    list.reduce((acc, l) => acc + parseFloat(l.total), 0);

  const totalGeneral = sum(segmentos.general);
  const totalNexo = sum(segmentos.nexo);
  const totalFacturan = sum(segmentos.facturan);

  return {
    totalGeneral,
    totalNexo,
    totalFacturan,
    // RN-35: facturan NEVER summed into general total
    totalSinFactura: totalGeneral + totalNexo,
  };
}

export function LiquidacionPeriodoPage() {
  const [periodo, setPeriodo] = useState<string>(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  });
  const [detalleLiq, setDetalleLiq] = useState<Liquidacion | null>(null);
  const [cerrarTarget, setCerrarTarget] = useState<Liquidacion | null>(null);

  const { data: liquidaciones, isLoading, error } = useLiquidaciones(
    periodo ? { periodo } : undefined,
  );
  const cerrarMutation = useCerrarLiquidacion();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <LoadingSpinner size="h-8 w-8" />
      </div>
    );
  }

  const items = liquidaciones ?? [];
  const segmentos = buildSegmentos(items);
  const kpis = buildKpis(segmentos);

  const handleCerrar = (liq: Liquidacion) => setCerrarTarget(liq);
  const handleConfirmCerrar = () => {
    if (cerrarTarget) {
      cerrarMutation.mutate(cerrarTarget.id);
      setCerrarTarget(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Liquidaciones del Período
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Vista segmentada: General / NEXO / Facturadores
          </p>
        </div>

        {/* Period filter */}
        <div className="flex items-center gap-2">
          <label
            htmlFor="periodo-filter"
            className="text-sm font-medium text-gray-700"
          >
            Período
          </label>
          <input
            id="periodo-filter"
            type="month"
            value={periodo}
            onChange={(e) => setPeriodo(e.target.value)}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
      </div>

      {/* KPI Header */}
      <LiquidacionKpiHeader kpis={kpis} />

      {/* Segmento General */}
      <SegmentoLiquidacionTable
        titulo="Segmento General"
        descripcion="Docentes no NEXO que no facturan"
        items={segmentos.general}
        isLoading={isLoading}
        error={error?.message ?? null}
        onVerDetalle={setDetalleLiq}
        onCerrar={handleCerrar}
      />

      {/* Segmento NEXO */}
      <SegmentoLiquidacionTable
        titulo="Segmento NEXO"
        descripcion="Docentes NEXO"
        items={segmentos.nexo}
        isLoading={isLoading}
        error={error?.message ?? null}
        onVerDetalle={setDetalleLiq}
        onCerrar={handleCerrar}
      />

      {/* Docentes Facturadores — informational only (RN-35) */}
      <SegmentoLiquidacionTable
        titulo="Docentes Facturadores"
        descripcion="Estos docentes emiten factura. Su monto es solo informativo y NO se suma al total general (RN-35)."
        items={segmentos.facturan}
        isLoading={isLoading}
        error={error?.message ?? null}
        informativo
        onVerDetalle={setDetalleLiq}
      />

      {/* Detalle Dialog */}
      <DetalleDocenteDialog
        liquidacion={detalleLiq}
        onClose={() => setDetalleLiq(null)}
      />

      {/* Confirm cerrar dialog */}
      <ConfirmDialog
        isOpen={cerrarTarget !== null}
        title="Cerrar liquidación"
        message="Esta acción es irreversible. ¿Confirmar cierre de la liquidación?"
        confirmLabel="Sí, cerrar"
        cancelLabel="Cancelar"
        variant="danger"
        onConfirm={handleConfirmCerrar}
        onCancel={() => setCerrarTarget(null)}
      />
    </div>
  );
}
