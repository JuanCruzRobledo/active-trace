import { useState, useMemo } from "react";
import { useParams } from "react-router-dom";
import { Input } from "@/shared/components/Input";
import { LoadingSpinner } from "@/shared/components/LoadingSpinner";
import { ErrorMessage } from "@/shared/components/ErrorMessage";
import { useAtrasados } from "@/features/comision/hooks/useAtrasados";

function RiesgoBadge({ riesgo }: { riesgo: string }) {
  const styles: Record<string, string> = {
    alto: "bg-red-100 text-red-800",
    medio: "bg-yellow-100 text-yellow-800",
    bajo: "bg-green-100 text-green-800",
  };
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
        styles[riesgo] ?? "bg-gray-100 text-gray-800"
      }`}
    >
      {riesgo}
    </span>
  );
}

export function AtrasadosPage() {
  const { materiaId } = useParams<{ materiaId: string }>();
  const [nombreFilter, setNombreFilter] = useState("");
  const { data, isLoading, isError, error } = useAtrasados(materiaId!);

  const items = useMemo(() => {
    const raw = data?.items ?? [];
    if (!nombreFilter) return raw;
    const q = nombreFilter.toLowerCase();
    return raw.filter((row) => row.alumno.toLowerCase().includes(q));
  }, [data, nombreFilter]);

  const isEmpty = !isLoading && !isError && items.length === 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Alumnos atrasados
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Alumnos identificados como en riesgo según el umbral configurado
        </p>
      </div>

      <div className="flex flex-wrap gap-3 rounded-lg border bg-white p-4 shadow-sm">
        <div className="w-64">
          <label className="mb-1 block text-xs font-medium text-gray-600">
            Buscar por nombre
          </label>
          <Input
            placeholder="Filtrar por nombre o apellido..."
            value={nombreFilter}
            onChange={(e) => setNombreFilter(e.target.value)}
          />
        </div>
        {nombreFilter && (
          <div className="flex items-end">
            <button
              type="button"
              onClick={() => setNombreFilter("")}
              className="rounded-md px-3 py-2 text-sm text-gray-500 hover:text-gray-700"
            >
              Limpiar
            </button>
          </div>
        )}
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="h-8 w-8" />
        </div>
      )}

      {isError && (
        <ErrorMessage
          message={error?.message ?? "Error al cargar datos de atrasados."}
        />
      )}

      {isEmpty && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-8 text-center">
          <p className="text-lg font-medium text-green-800">
            No hay alumnos atrasados en esta materia
          </p>
          <p className="mt-1 text-sm text-green-600">
            Todos los alumnos cumplen con el umbral de aprobación configurado.
          </p>
        </div>
      )}

      {!isLoading && !isError && items.length > 0 && (
        <div className="overflow-x-auto rounded-lg border bg-white shadow-sm">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">
                  Alumno
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">
                  Legajo
                </th>
                <th className="px-4 py-3 text-center font-medium text-gray-500">
                  Act. faltantes
                </th>
                <th className="px-4 py-3 text-center font-medium text-gray-500">
                  Nota actual
                </th>
                <th className="px-4 py-3 text-center font-medium text-gray-500">
                  Estado
                </th>
                <th className="px-4 py-3 text-center font-medium text-gray-500">
                  Riesgo
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((row) => (
                <tr key={row.alumno_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {row.alumno}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{row.legajo}</td>
                  <td className="px-4 py-3 text-center">
                    {row.actividades_faltantes}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {row.nota_actual ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                        row.estado === "atrasado"
                          ? "bg-red-100 text-red-800"
                          : "bg-green-100 text-green-800"
                      }`}
                    >
                      {row.estado === "atrasado" ? "Atrasado" : "Al día"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <RiesgoBadge riesgo={row.riesgo} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="border-t bg-gray-50 px-4 py-2 text-sm text-gray-500">
            {data?.total ?? items.length} alumno(s)
          </div>
        </div>
      )}
    </div>
  );
}
