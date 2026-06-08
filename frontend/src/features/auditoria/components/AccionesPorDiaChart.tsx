import type { AccionPorDia } from "@/features/auditoria/types/auditoria";
import { LoadingSpinner } from "@/shared/components/LoadingSpinner";

interface AccionesPorDiaChartProps {
  data: AccionPorDia[];
  isLoading?: boolean;
  error?: string | null;
}

export function AccionesPorDiaChart({
  data,
  isLoading,
  error,
}: AccionesPorDiaChartProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <LoadingSpinner size="h-6 w-6" />
      </div>
    );
  }

  if (error) {
    return (
      <p className="text-sm text-red-600">{error}</p>
    );
  }

  const max = Math.max(...data.map((d) => d.cantidad), 1);

  return (
    <div className="space-y-2" aria-label="Acciones por día">
      {data.length === 0 && (
        <p className="text-sm text-gray-400">Sin datos para el período</p>
      )}
      {data.map((d) => (
        <div key={d.fecha} className="flex items-center gap-3">
          <span className="w-24 shrink-0 text-xs text-gray-500">{d.fecha}</span>
          <div className="flex-1 rounded-full bg-gray-100">
            <div
              className="h-4 rounded-full bg-brand-500"
              style={{ width: `${(d.cantidad / max) * 100}%` }}
              role="progressbar"
              aria-valuenow={d.cantidad}
              aria-valuemax={max}
            />
          </div>
          <span className="w-10 text-right text-xs font-semibold text-gray-700">
            {d.cantidad}
          </span>
        </div>
      ))}
    </div>
  );
}
