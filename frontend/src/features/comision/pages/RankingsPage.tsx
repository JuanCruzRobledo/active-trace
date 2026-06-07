import { useState } from "react";
import { useParams } from "react-router-dom";
import { LoadingSpinner } from "@/shared/components/LoadingSpinner";
import { ErrorMessage } from "@/shared/components/ErrorMessage";
import {
  useRanking,
  useNotasFinales,
} from "@/features/comision/hooks/useRanking";

type ViewMode = "ranking" | "notas-finales";

export function RankingsPage() {
  const { materiaId } = useParams<{ materiaId: string }>();
  const [view, setView] = useState<ViewMode>("ranking");

  const rankingQuery = useRanking(materiaId!);
  const notasQuery = useNotasFinales(materiaId!);

  const isRankingView = view === "ranking";
  const activeQuery = isRankingView ? rankingQuery : notasQuery;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {isRankingView ? "Ranking de actividades" : "Notas finales"}
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            {isRankingView
              ? "Alumnos ordenados por cantidad de actividades aprobadas"
              : "Notas finales calculadas por alumno"}
          </p>
        </div>

        <div className="flex rounded-lg border border-gray-300 bg-white text-sm">
          <button
            type="button"
            onClick={() => setView("ranking")}
            className={`rounded-l-lg px-4 py-2 font-medium transition-colors ${
              isRankingView
                ? "bg-brand-600 text-white"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            Ranking
          </button>
          <button
            type="button"
            onClick={() => setView("notas-finales")}
            className={`rounded-r-lg px-4 py-2 font-medium transition-colors ${
              !isRankingView
                ? "bg-brand-600 text-white"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            Notas finales
          </button>
        </div>
      </div>

      {activeQuery.isLoading && (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="h-8 w-8" />
        </div>
      )}

      {activeQuery.isError && (
        <ErrorMessage
          message={
            activeQuery.error?.message ??
            "Error al cargar los datos."
          }
        />
      )}

      {!activeQuery.isLoading && !activeQuery.isError && (
        <>
          {(isRankingView
            ? rankingQuery.data?.items ?? []
            : notasQuery.data?.items ?? []
          ).length === 0 ? (
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center">
              <p className="text-lg font-medium text-gray-700">
                {isRankingView
                  ? "Aún no hay datos de actividades aprobadas"
                  : "Aún no hay notas finales calculadas"}
              </p>
              <p className="mt-1 text-sm text-gray-500">
                {isRankingView
                  ? "Importá calificaciones para ver el ranking."
                  : "Completá la importación para calcular notas finales."}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-lg border bg-white shadow-sm">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-gray-500">
                      #
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-gray-500">
                      Alumno
                    </th>
                    {isRankingView ? (
                      <>
                        <th className="px-4 py-3 text-center font-medium text-gray-500">
                          Aprobadas
                        </th>
                        <th className="px-4 py-3 text-center font-medium text-gray-500">
                          Total
                        </th>
                        <th className="px-4 py-3 text-center font-medium text-gray-500">
                          Porcentaje
                        </th>
                      </>
                    ) : (
                      <th className="px-4 py-3 text-right font-medium text-gray-500">
                        Nota final
                      </th>
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {(isRankingView
                    ? rankingQuery.data!.items
                    : notasQuery.data!.items
                  ).map((row, i) => (
                    <tr key={row.alumno_id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-gray-400">{i + 1}</td>
                      <td className="px-4 py-3 font-medium text-gray-900">
                        {row.alumno}
                      </td>
                      {isRankingView ? (
                        <>
                          <td className="px-4 py-3 text-center">
                            {(row as any).actividades_aprobadas}
                          </td>
                          <td className="px-4 py-3 text-center">
                            {(row as any).total_actividades}
                          </td>
                          <td className="px-4 py-3 text-center">
                            {(row as any).porcentaje}%
                          </td>
                        </>
                      ) : (
                        <td className="px-4 py-3 text-right font-semibold">
                          {(row as any).nota_final}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
