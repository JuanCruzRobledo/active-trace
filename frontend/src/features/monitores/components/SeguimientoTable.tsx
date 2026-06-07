import type { MonitorRow } from "@/features/monitores/services/seguimiento";

interface SeguimientoTableProps {
  items: MonitorRow[];
  total: number;
}

export function SeguimientoTable({ items, total }: SeguimientoTableProps) {
  if (items.length === 0) return null;

  return (
    <div className="overflow-x-auto rounded-lg border bg-white shadow-sm">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium text-gray-500">Alumno</th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">Correo</th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">Comisión</th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">Materia</th>
            <th className="px-4 py-3 text-left font-medium text-gray-500">Actividad</th>
            <th className="px-4 py-3 text-center font-medium text-gray-500">Estado</th>
            <th className="px-4 py-3 text-right font-medium text-gray-500">Nota</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {items.map((row, i) => (
            <tr key={`${row.alumno_id}-${i}`} className="hover:bg-gray-50">
              <td className="px-4 py-3 font-medium text-gray-900">{row.alumno}</td>
              <td className="px-4 py-3 text-gray-500">{row.correo}</td>
              <td className="px-4 py-3 text-gray-500">{row.comision}</td>
              <td className="px-4 py-3 text-gray-500">{row.materia}</td>
              <td className="px-4 py-3 text-gray-500">{row.actividad}</td>
              <td className="px-4 py-3 text-center">
                <span
                  className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                    row.estado === "aprobada"
                      ? "bg-green-100 text-green-800"
                      : row.estado === "pendiente"
                        ? "bg-yellow-100 text-yellow-800"
                        : "bg-gray-100 text-gray-800"
                  }`}
                >
                  {row.estado}
                </span>
              </td>
              <td className="px-4 py-3 text-right">{row.nota ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="border-t bg-gray-50 px-4 py-2 text-sm text-gray-500">
        {total} registro(s)
      </div>
    </div>
  );
}
