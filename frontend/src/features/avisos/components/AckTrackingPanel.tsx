import type { TrackingAvisoResponse } from "@/features/avisos/types/avisos";

interface AckTrackingPanelProps {
  tracking: TrackingAvisoResponse;
}

export function AckTrackingPanel({ tracking }: AckTrackingPanelProps) {
  const acknowledgments = tracking.acknowledgments ?? [];

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-gray-700">
        Usuarios ({tracking.total_usuarios})
      </h3>
      <div className="max-h-80 overflow-y-auto rounded-md border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Usuario
              </th>
              <th className="px-3 py-2 text-center text-xs font-medium uppercase tracking-wider text-gray-500">
                Confirmado
              </th>
              <th className="px-3 py-2 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Fecha
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {acknowledgments.map((item) => (
              <tr
                key={item.usuario_id}
                className="hover:bg-gray-50"
              >
                <td className="px-3 py-2 text-gray-900">
                  {item.usuario_nombre ?? item.usuario_id.slice(0, 8)}
                </td>
                <td className="px-3 py-2 text-center">
                  {item.confirmado_at ? (
                    <svg
                      className="mx-auto h-5 w-5 text-green-500"
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                      aria-hidden="true"
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
                        clipRule="evenodd"
                      />
                    </svg>
                  ) : (
                    <svg
                      className="mx-auto h-5 w-5 text-gray-300"
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                      aria-hidden="true"
                    >
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v3.586L7.707 9.293a1 1 0 00-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 10.586V7z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                </td>
                <td className="px-3 py-2 text-right text-gray-500">
                  {item.confirmado_at
                    ? new Date(item.confirmado_at).toLocaleDateString()
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
