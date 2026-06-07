import { useParams } from "react-router-dom";
import { Button } from "@/shared/components/Button";
import { LoadingSpinner } from "@/shared/components/LoadingSpinner";
import { ErrorMessage } from "@/shared/components/ErrorMessage";
import { useReportes } from "@/features/comision/hooks/useReportes";
import { exportarEntregasSinCorregir } from "@/features/comision/services/reportes";

function MetricCard({
  label,
  value,
  unit,
}: {
  label: string;
  value: string | number;
  unit?: string;
}) {
  return (
    <div className="rounded-lg border bg-white p-5 shadow-sm">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="mt-1 text-3xl font-bold text-gray-900">
        {value}
        {unit && <span className="ml-1 text-lg font-normal text-gray-500">{unit}</span>}
      </p>
    </div>
  );
}

export function ReportesPage() {
  const { materiaId } = useParams<{ materiaId: string }>();
  const { data, isLoading, isError, error } = useReportes(materiaId!);

  const handleExport = async () => {
    try {
      const blob = await exportarEntregasSinCorregir(materiaId!);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `entregas-pendientes-${materiaId}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // Error is handled by the catch below
    }
  };

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
        message={error?.message ?? "Error al cargar los reportes."}
      />
    );
  }

  if (!data?.tiene_datos) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reportes</h1>
          <p className="mt-1 text-sm text-gray-500">
            Métricas consolidadas de la materia
          </p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center">
          <p className="text-lg font-medium text-gray-700">
            No hay datos disponibles
          </p>
          <p className="mt-1 text-sm text-gray-500">
            Importe calificaciones primero para ver las métricas.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Reportes</h1>
        <p className="mt-1 text-sm text-gray-500">
          Métricas consolidadas de la materia
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <MetricCard label="Total alumnos" value={data.total_alumnos} />
        <MetricCard
          label="Actividades registradas"
          value={data.actividades_registradas}
        />
        <MetricCard
          label="% Aprobación"
          value={data.porcentaje_aprobacion}
          unit="%"
        />
        <MetricCard label="Alumnos atrasados" value={data.alumnos_atrasados} />
        <MetricCard label="Alumnos al día" value={data.alumnos_al_dia} />
      </div>

      <div>
        <Button variant="secondary" onClick={handleExport}>
          Exportar entregas sin corregir
        </Button>
      </div>
    </div>
  );
}
