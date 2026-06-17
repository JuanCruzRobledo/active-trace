import { useState } from "react";
import { FilterableTable } from "@/shared/components/FilterableTable";
import { LoadingSpinner } from "@/shared/components/LoadingSpinner";
import {
  useConvocatorias,
  useAgenda,
} from "@/features/coloquios/hooks/useColoquios";
import type { Column } from "@/shared/components/FilterableTable";

const estado_colors: Record<string, string> = {
  abierta: "bg-green-100 text-green-800",
  cerrada: "bg-gray-100 text-gray-600",
  en_curso: "bg-blue-100 text-blue-800",
};

const agenda_estado_colors: Record<string, string> = {
  confirmada: "bg-green-100 text-green-800",
  pendiente: "bg-yellow-100 text-yellow-800",
  cancelada: "bg-red-100 text-red-800",
};

export function ColoquiosAdminPage() {
  const [selectedEvalId, setSelectedEvalId] = useState<string | undefined>();
  const { data: convocatorias, isLoading: loadingConv } = useConvocatorias();
  const { data: agenda, isLoading: loadingAgenda } =
    useAgenda(selectedEvalId);

  const convItems =
    (convocatorias?.items ?? []) as unknown as Record<string, unknown>[];

  const agendaItems = (agenda ?? []) as unknown as Record<string, unknown>[];

  const convColumns: Column<Record<string, unknown>>[] = [
    { key: "instancia", label: "Convocatoria", sortable: true },
    {
      key: "estado",
      label: "Estado",
      sortable: true,
      render: (row) => {
        const est = (row.estado as string) ?? "abierta";
        return (
          <span
            className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${estado_colors[est] ?? "bg-gray-100 text-gray-800"}`}
          >
            {est}
          </span>
        );
      },
    },
  ];

  const agendaColumns: Column<Record<string, unknown>>[] = [
    { key: "fecha", label: "Fecha", sortable: true },
    { key: "alumno", label: "Alumno", sortable: true },
    {
      key: "estado",
      label: "Estado",
      sortable: true,
      render: (row) => {
        const est = (row.estado as string) ?? "pendiente";
        return (
          <span
            className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${agenda_estado_colors[est] ?? "bg-gray-100 text-gray-800"}`}
          >
            {est}
          </span>
        );
      },
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Admin Coloquios
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Vista global de convocatorias y agenda de reservas
        </p>
      </div>

      {/* Convocatorias activas */}
      <section>
        <h2 className="mb-4 text-lg font-semibold text-gray-800">
          Convocatorias
        </h2>
        <FilterableTable
          columns={convColumns}
          data={convItems}
          total={convocatorias?.total ?? convItems.length}
          isLoading={loadingConv}
          error={null}
          exportFileName="convocatorias-admin.csv"
        />
      </section>

      {/* Selector de convocatoria + Agenda */}
      <section>
        <h2 className="mb-4 text-lg font-semibold text-gray-800">
          Agenda de Reservas
        </h2>

        <div className="mb-4">
          <select
            value={selectedEvalId ?? ""}
            onChange={(e) =>
              setSelectedEvalId(e.target.value || undefined)
            }
            className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">Seleccioná una convocatoria</option>
            {convItems.map((item) => (
              <option key={item.id as string} value={item.id as string}>
                {item.instancia as string}
              </option>
            ))}
          </select>
        </div>

        {loadingAgenda && (
          <div className="flex items-center justify-center py-8">
            <LoadingSpinner size="h-6 w-6" />
          </div>
        )}

        {!loadingAgenda && !selectedEvalId && (
          <p className="py-8 text-center text-sm text-gray-400">
            Seleccioná una convocatoria para ver su agenda
          </p>
        )}

        {!loadingAgenda && selectedEvalId && (
          <FilterableTable
            columns={agendaColumns}
            data={agendaItems}
            total={agendaItems.length}
            exportFileName="agenda.csv"
          />
        )}
      </section>
    </div>
  );
}
