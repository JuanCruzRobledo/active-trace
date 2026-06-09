import { LoadingSpinner } from "@/shared/components/LoadingSpinner";
import { ErrorMessage } from "@/shared/components/ErrorMessage";
import { useMetricas } from "@/features/coloquios/hooks/useColoquios";

interface MetricCardProps {
  label: string;
  value: number | string;
  color: string;
}

function MetricCard({ label, value, color }: MetricCardProps) {
  return (
    <div className="rounded-lg border bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-gray-500">{label}</p>
      <p className={`mt-2 text-3xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

export function ColoquiosPanelPage() {
  const { data: metricas, isLoading, isError, error } = useMetricas();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="h-8 w-8" />
      </div>
    );
  }

  if (isError) {
    return (
      <ErrorMessage
        message={error?.message ?? "Error al cargar métricas de coloquios."}
      />
    );
  }

  const cards = [
    { label: "Total Evaluaciones", value: metricas?.total_evaluaciones ?? 0, color: "text-brand-600" },
    { label: "Activas", value: metricas?.activas ?? 0, color: "text-green-600" },
    { label: "Alumnos Convocados", value: metricas?.total_alumnos_convocados ?? 0, color: "text-blue-600" },
    { label: "Reservas", value: metricas?.total_reservas ?? 0, color: "text-amber-600" },
    { label: "Notas Cargadas", value: metricas?.notas_cargadas ?? 0, color: "text-purple-600" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Panel de Coloquios</h1>
        <p className="mt-1 text-sm text-gray-500">
          Métricas generales del módulo de coloquios
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {cards.map((card) => (
          <MetricCard
            key={card.label}
            label={card.label}
            value={card.value}
            color={card.color}
          />
        ))}
      </div>
    </div>
  );
}
