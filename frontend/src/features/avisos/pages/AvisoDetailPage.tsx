import { useParams, useNavigate } from "react-router-dom";
import { LoadingSpinner } from "@/shared/components/LoadingSpinner";
import { ErrorMessage } from "@/shared/components/ErrorMessage";
import { Button } from "@/shared/components/Button";
import {
  useAvisoById,
  useAcknowledgeAviso,
  useTracking,
} from "@/features/avisos/hooks/useAvisos";
import { AckTrackingPanel } from "@/features/avisos/components/AckTrackingPanel";

function SeveridadBadge({ severidad }: { severidad: string }) {
  const styles: Record<string, string> = {
    critical: "bg-red-100 text-red-800",
    warning: "bg-yellow-100 text-yellow-800",
    info: "bg-blue-100 text-blue-800",
  };
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
        styles[severidad] ?? "bg-gray-100 text-gray-800"
      }`}
    >
      {severidad}
    </span>
  );
}

export function AvisoDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: aviso, isLoading, isError, error } = useAvisoById(id!);
  const { data: tracking } = useTracking(id!);
  const acknowledgeAviso = useAcknowledgeAviso();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="h-8 w-8" />
      </div>
    );
  }

  if (isError) {
    return (
      <ErrorMessage message={error?.message ?? "Error al cargar el aviso"} />
    );
  }

  if (!aviso) return null;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{aviso.titulo}</h1>
          <p className="mt-1 text-sm text-gray-500">
            Creado el {aviso.created_at ? new Date(aviso.created_at).toLocaleDateString() : "—"}
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            onClick={() => navigate(`/avisos/${id}/editar`)}
          >
            Editar
          </Button>
          <Button
            variant="secondary"
            onClick={() => navigate("/avisos")}
          >
            Volver
          </Button>
        </div>
      </div>

      <div className="rounded-lg border bg-white p-6 shadow-sm">
        <div className="mb-4 flex flex-wrap gap-3">
          <SeveridadBadge severidad={aviso.severidad} />
          <span className="inline-block rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
            {aviso.alcance}
          </span>
          <span
            className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
              aviso.activo
                ? "bg-green-100 text-green-800"
                : "bg-gray-100 text-gray-400"
            }`}
          >
            {aviso.activo ? "Activo" : "Inactivo"}
          </span>
          {aviso.requiere_ack && (
            <span className="inline-block rounded-full bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-800">
              Requiere confirmación
            </span>
          )}
        </div>

        <div className="prose prose-sm max-w-none text-gray-700">
          <p>{aviso.cuerpo}</p>
        </div>

        <div className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
          <div>
            <span className="font-medium text-gray-600">Inicio:</span>{" "}
            {new Date(aviso.inicio_en).toLocaleDateString()}
          </div>
          <div>
            <span className="font-medium text-gray-600">Fin:</span>{" "}
            {new Date(aviso.fin_en).toLocaleDateString()}
          </div>
          {aviso.materia_id && (
            <div>
              <span className="font-medium text-gray-600">Materia:</span>{" "}
              {aviso.materia_nombre ?? aviso.materia_id}
            </div>
          )}
          {aviso.cohorte_id && (
            <div>
              <span className="font-medium text-gray-600">Cohorte:</span>{" "}
              {aviso.cohorte_nombre ?? aviso.cohorte_id}
            </div>
          )}
          {aviso.rol_destino && (
            <div>
              <span className="font-medium text-gray-600">Rol destino:</span>{" "}
              {aviso.rol_destino}
            </div>
          )}
        </div>
      </div>

      {aviso.requiere_ack && (
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-800">
              Confirmaciones
            </h2>
            <Button
              onClick={() => acknowledgeAviso.mutate(id!)}
              is_loading={acknowledgeAviso.isPending}
              disabled={tracking?.acknowledgments?.some(
                (a) => a.usuario_id === "me" && a.confirmado_at,
              )}
            >
              Confirmar lectura
            </Button>
          </div>
          {tracking && (
            <div className="mb-4">
              <div className="flex items-center gap-2 text-sm">
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-gray-200">
                  <div
                    className="h-full rounded-full bg-brand-600 transition-all"
                    style={{ width: `${tracking.porcentaje}%` }}
                  />
                </div>
                <span className="text-xs text-gray-500">
                  {tracking.total_ack}/{tracking.total_usuarios} (
                  {tracking.porcentaje}%)
                </span>
              </div>
            </div>
          )}
          {tracking && <AckTrackingPanel tracking={tracking} />}
        </div>
      )}
    </div>
  );
}
