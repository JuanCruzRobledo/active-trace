import type { InteraccionPorDocenteMateria } from "@/features/auditoria/types/auditoria";
import { LoadingSpinner } from "@/shared/components/LoadingSpinner";

interface InteraccionesPanelProps {
  data: InteraccionPorDocenteMateria[];
  isLoading?: boolean;
  error?: string | null;
}

export function InteraccionesPanel({
  data,
  isLoading,
  error,
}: InteraccionesPanelProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <LoadingSpinner size="h-6 w-6" />
      </div>
    );
  }

  if (error) {
    return <p className="text-sm text-red-600">{error}</p>;
  }

  const sorted = [...data].sort((a, b) => b.total - a.total);

  return (
    <div className="overflow-hidden rounded-lg border bg-white">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              Docente
            </th>
            <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              Materia
            </th>
            <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
              Interacciones
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {sorted.length === 0 && (
            <tr>
              <td
                colSpan={3}
                className="px-4 py-4 text-center text-gray-400"
              >
                Sin datos
              </td>
            </tr>
          )}
          {sorted.map((d) => (
            <tr
              key={`${d.usuario_id}-${d.materia_id}`}
              className="hover:bg-gray-50"
            >
              <td className="px-4 py-2 text-gray-700">
                {d.nombre ?? (
                  <code className="text-xs text-gray-500">
                    {d.usuario_id.slice(0, 8)}...
                  </code>
                )}
              </td>
              <td className="px-4 py-2 text-gray-700">
                {d.materia_nombre ?? (
                  <code className="text-xs text-gray-500">
                    {d.materia_id.slice(0, 8)}...
                  </code>
                )}
              </td>
              <td className="px-4 py-2 text-right font-semibold text-gray-900">
                {d.total}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
