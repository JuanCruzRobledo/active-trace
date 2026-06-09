import { useState } from "react";
import { useParams } from "react-router-dom";
import { Button } from "@/shared/components/Button";
import { Input } from "@/shared/components/Input";
import { FormField } from "@/shared/components/FormField";
import { LoadingSpinner } from "@/shared/components/LoadingSpinner";
import { ErrorMessage } from "@/shared/components/ErrorMessage";
import {
  useComunicaciones,
  useAlumnosAtrasadosParaComunicacion,
  useCrearComunicacion,
  useComunicacionPolling,
} from "@/features/comision/hooks/useComunicaciones";
import type { ComunicacionEstado } from "@/features/comision/services/comunicaciones";

function EstadoBadge({ estado }: { estado: ComunicacionEstado }) {
  const styles: Record<string, string> = {
    Pendiente: "bg-yellow-100 text-yellow-800",
    "En envío": "bg-blue-100 text-blue-800",
    Enviado: "bg-green-100 text-green-800",
    Fallido: "bg-red-100 text-red-800",
    Cancelado: "bg-gray-100 text-gray-800",
  };
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
        styles[estado] ?? "bg-gray-100 text-gray-800"
      }`}
    >
      {estado}
    </span>
  );
}

type Step = "list" | "editor" | "preview";

export function ComunicacionesPage() {
  const { materiaId } = useParams<{ materiaId: string }>();
  const [step, setStep] = useState<Step>("list");
  const [asunto, setAsunto] = useState("");
  const [cuerpo, setCuerpo] = useState("");
  const [selectedDestinatarios, setSelectedDestinatarios] = useState<string[]>([]);
  const [trackingId, setTrackingId] = useState<string | null>(null);

  const comunicacionesQuery = useComunicaciones();
  const destinatariosQuery = useAlumnosAtrasadosParaComunicacion(materiaId!);
  const crearMutation = useCrearComunicacion();
  const trackingQuery = useComunicacionPolling(
    trackingId,
    trackingId !== null,
  );

  const handleStartNew = () => {
    setAsunto("");
    setCuerpo("");
    setSelectedDestinatarios([]);
    setTrackingId(null);
    setStep("editor");
    destinatariosQuery.refetch();
  };

  const handlePreview = () => {
    setStep("preview");
  };

  const handleSend = () => {
    crearMutation.mutate(
      {
        materia_id: materiaId!,
        asunto,
        cuerpo,
        destinatarios: selectedDestinatarios,
      },
      {
        onSuccess: (result) => {
          setTrackingId(result.id);
          setStep("list");
          comunicacionesQuery.refetch();
        },
      },
    );
  };

  const toggleDestinatario = (id: string) => {
    setSelectedDestinatarios((prev) =>
      prev.includes(id)
        ? prev.filter((d) => d !== id)
        : [...prev, id],
    );
  };

  const trackingItem = trackingQuery.data;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Comunicaciones</h1>
          <p className="mt-1 text-sm text-gray-500">
            Comunicaciones masivas a alumnos atrasados
          </p>
        </div>
        {step === "list" && (
          <Button onClick={handleStartNew}>Nueva comunicación</Button>
        )}
        {step === "editor" && (
          <Button variant="secondary" onClick={() => setStep("list")}>
            Volver
          </Button>
        )}
      </div>

      {trackingId && trackingItem && (
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-900">
                Comunicación: {trackingItem.asunto}
              </p>
              <p className="mt-1 text-sm text-gray-500">
                {trackingItem.enviados} de {trackingItem.total_destinatarios} enviados
                {trackingItem.fallidos > 0 && ` (${trackingItem.fallidos} fallidos)`}
              </p>
            </div>
            <EstadoBadge estado={trackingItem.estado} />
          </div>
          {(trackingItem.estado === "Pendiente" || trackingItem.estado === "En envío") && (
            <div className="mt-3">
              <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
                <div
                  className="h-full rounded-full bg-brand-600 transition-all duration-500"
                  style={{
                    width: `${Math.round(
                      (trackingItem.enviados / trackingItem.total_destinatarios) * 100,
                    )}%`,
                  }}
                />
              </div>
              <p className="mt-1 text-xs text-gray-500">Enviando... {trackingItem.estado === "En envío" && "Actualizando"}</p>
            </div>
          )}
          {trackingItem.estado === "Fallido" && (
            <div className="mt-3">
              <p className="text-sm text-red-600">
                La comunicación no pudo completarse. Revisá los destinatarios e intentá de nuevo.
              </p>
              <Button
                variant="secondary"
                className="mt-2"
                onClick={() => {
                  setTrackingId(null);
                  handleStartNew();
                }}
              >
                Reintentar
              </Button>
            </div>
          )}
        </div>
      )}

      {step === "list" && (
        <>
          {comunicacionesQuery.isLoading && (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner size="h-8 w-8" />
            </div>
          )}
          {comunicacionesQuery.isError && (
            <ErrorMessage
              message={
                comunicacionesQuery.error?.message ??
                "Error al cargar comunicaciones."
              }
            />
          )}
          {!comunicacionesQuery.isLoading &&
            !comunicacionesQuery.isError && (
              <div className="overflow-x-auto rounded-lg border bg-white shadow-sm">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium text-gray-500">
                        Asunto
                      </th>
                      <th className="px-4 py-3 text-center font-medium text-gray-500">
                        Estado
                      </th>
                      <th className="px-4 py-3 text-center font-medium text-gray-500">
                        Destinatarios
                      </th>
                      <th className="px-4 py-3 text-right font-medium text-gray-500">
                        Fecha
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {(comunicacionesQuery.data?.items ?? []).map((item) => (
                      <tr key={item.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium text-gray-900">
                          {item.asunto}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <EstadoBadge estado={item.estado} />
                        </td>
                        <td className="px-4 py-3 text-center text-gray-500">
                          {item.total_destinatarios}
                        </td>
                        <td className="px-4 py-3 text-right text-gray-500">
                          {new Date(item.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                    {(comunicacionesQuery.data?.items ?? []).length === 0 && (
                      <tr>
                        <td
                          colSpan={4}
                          className="px-4 py-8 text-center text-gray-500"
                        >
                          No hay comunicaciones enviadas aún.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
        </>
      )}

      {step === "editor" && (
        <div className="space-y-4 rounded-lg border bg-white p-6 shadow-sm">
          <FormField label="Asunto" html_for="asunto">
            <Input
              id="asunto"
              value={asunto}
              onChange={(e) => setAsunto(e.target.value)}
              placeholder="Asunto del mensaje"
            />
          </FormField>

          <FormField label="Cuerpo del mensaje" html_for="cuerpo">
            <textarea
              id="cuerpo"
              value={cuerpo}
              onChange={(e) => setCuerpo(e.target.value)}
              rows={5}
              placeholder="Escribí el mensaje..."
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-gray-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-1"
            />
          </FormField>

          <div>
            <p className="mb-2 text-sm font-medium text-gray-700">
              Destinatarios (alumnos atrasados)
            </p>
            {destinatariosQuery.isLoading && <LoadingSpinner />}
            {destinatariosQuery.isError && (
              <p className="text-sm text-red-600">
                Error al cargar destinatarios.
              </p>
            )}
            {destinatariosQuery.data && (
              <div className="max-h-48 space-y-1 overflow-y-auto rounded-md border p-2">
                {destinatariosQuery.data
                  .filter((d) => d.seleccionado)
                  .map((d) => (
                    <label
                      key={d.alumno_id}
                      className="flex items-center gap-2 rounded px-2 py-1 text-sm hover:bg-gray-50"
                    >
                      <input
                        type="checkbox"
                        checked={selectedDestinatarios.includes(d.alumno_id)}
                        onChange={() => toggleDestinatario(d.alumno_id)}
                        className="h-4 w-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
                      />
                      {d.alumno} ({d.legajo})
                    </label>
                  ))}
                {destinatariosQuery.data.filter((d) => d.seleccionado).length ===
                  0 && (
                  <p className="p-2 text-sm text-gray-400">
                    No hay alumnos atrasados para comunicar.
                  </p>
                )}
              </div>
            )}
          </div>

          <div className="flex gap-3">
            <Button
              onClick={handlePreview}
              disabled={!asunto || !cuerpo || selectedDestinatarios.length === 0}
            >
              Previsualizar
            </Button>
          </div>
        </div>
      )}

      {step === "preview" && (
        <div className="space-y-4 rounded-lg border bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">
            Vista previa del mensaje
          </h2>

          <div className="rounded-md border bg-gray-50 p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
              Asunto
            </p>
            <p className="mt-1 text-sm font-medium text-gray-900">{asunto}</p>
          </div>

          <div className="rounded-md border bg-gray-50 p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
              Cuerpo
            </p>
            <p className="mt-1 whitespace-pre-wrap text-sm text-gray-700">
              {cuerpo}
            </p>
          </div>

          <div className="rounded-md border bg-gray-50 p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
              Destinatarios
            </p>
            <p className="mt-1 text-sm text-gray-700">
              {selectedDestinatarios.length} alumno(s)
            </p>
          </div>

          <div className="flex gap-3">
            <Button
              onClick={handleSend}
              is_loading={crearMutation.isPending}
            >
              Enviar
            </Button>
            <Button variant="secondary" onClick={() => setStep("editor")}>
              Editar
            </Button>
          </div>

          {crearMutation.isError && (
            <ErrorMessage
              message={
                crearMutation.error?.message ??
                "Error al enviar la comunicación."
              }
              action_label="Reintentar"
              on_action={handleSend}
            />
          )}
        </div>
      )}
    </div>
  );
}
