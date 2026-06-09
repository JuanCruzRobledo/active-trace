import type { Liquidacion } from "@/features/liquidaciones/types/liquidaciones";

interface DetalleDocenteDialogProps {
  liquidacion: Liquidacion | null;
  onClose: () => void;
}

export function DetalleDocenteDialog({
  liquidacion,
  onClose,
}: DetalleDocenteDialogProps) {
  if (!liquidacion) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="detalle-docente-title"
    >
      <div className="w-full max-w-lg rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <h2
            id="detalle-docente-title"
            className="text-lg font-semibold text-gray-900"
          >
            Detalle de liquidación
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            className="rounded-md p-1 text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <svg
              className="h-5 w-5"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={2}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="space-y-4 p-6">
          <dl className="grid grid-cols-2 gap-4">
            <div>
              <dt className="text-xs font-medium uppercase tracking-wider text-gray-500">
                Docente (ID)
              </dt>
              <dd className="mt-1 font-mono text-sm text-gray-900">
                {liquidacion.usuario_id}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wider text-gray-500">
                Rol
              </dt>
              <dd className="mt-1 text-sm font-semibold text-gray-900">
                {liquidacion.rol}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wider text-gray-500">
                Período
              </dt>
              <dd className="mt-1 text-sm text-gray-900">{liquidacion.periodo}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wider text-gray-500">
                Comisiones
              </dt>
              <dd className="mt-1 text-sm text-gray-900">
                {liquidacion.comisiones}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wider text-gray-500">
                Monto base
              </dt>
              <dd className="mt-1 text-sm text-gray-900">
                ${liquidacion.monto_base}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium uppercase tracking-wider text-gray-500">
                Monto plus
              </dt>
              <dd className="mt-1 text-sm text-gray-900">
                ${liquidacion.monto_plus}
              </dd>
            </div>
            <div className="col-span-2">
              <dt className="text-xs font-medium uppercase tracking-wider text-gray-500">
                Total
              </dt>
              <dd className="mt-1 text-xl font-bold text-gray-900">
                ${liquidacion.total}
              </dd>
            </div>
          </dl>

          {liquidacion.excluido_por_factura && (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700">
              Este docente factura — su monto es informativo y no se suma al
              total general.
            </div>
          )}

          {liquidacion.es_nexo && (
            <div className="rounded-md border border-purple-200 bg-purple-50 p-3 text-sm text-purple-700">
              Docente NEXO
            </div>
          )}

          {liquidacion.estado === "cerrada" && liquidacion.cerrada_at && (
            <div className="rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-700">
              Liquidación cerrada el{" "}
              {new Date(liquidacion.cerrada_at).toLocaleDateString("es-AR")}
            </div>
          )}
        </div>

        <div className="flex justify-end border-t bg-gray-50 px-6 py-4 rounded-b-lg">
          <button
            type="button"
            onClick={onClose}
            className="inline-flex items-center justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
