import { useState } from "react";
import { Button } from "@/shared/components/Button";
import { Input } from "@/shared/components/Input";
import { LoadingSpinner } from "@/shared/components/LoadingSpinner";
import { ErrorMessage } from "@/shared/components/ErrorMessage";
import {
  useTareaById,
  useAgregarComentario,
  useActualizarEstadoTarea,
} from "@/features/tareas/hooks/useTareas";

const estado_colors: Record<string, string> = {
  pendiente: "bg-yellow-100 text-yellow-800",
  en_curso: "bg-blue-100 text-blue-800",
  completada: "bg-green-100 text-green-800",
  cancelada: "bg-gray-100 text-gray-600",
};

const timeline_order = ["pendiente", "en_curso", "completada", "cancelada"];

interface TareaDetailPanelProps {
  tareaId: string;
  onClose: () => void;
}

export function TareaDetailPanel({ tareaId, onClose }: TareaDetailPanelProps) {
  const { data: tarea, isLoading, isError, error } = useTareaById(tareaId);
  const agregarComentario = useAgregarComentario();
  const actualizarEstado = useActualizarEstadoTarea();
  const [nuevoComentario, setNuevoComentario] = useState("");

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="h-8 w-8" />
      </div>
    );
  }

  if (isError || !tarea) {
    return (
      <ErrorMessage
        message={error?.message ?? "Error al cargar la tarea."}
      />
    );
  }

  const idx_actual = timeline_order.indexOf(tarea.estado);

  const handleEnviarComentario = async () => {
    if (!nuevoComentario.trim()) return;
    await agregarComentario.mutateAsync({
      tareaId,
      payload: { texto: nuevoComentario },
    });
    setNuevoComentario("");
  };

  return (
    <div className="rounded-lg border bg-white shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-6 py-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            Detalle de Tarea
          </h3>
          <code className="mt-0.5 block text-xs text-gray-400">
            {tarea.id}
          </code>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
        >
          <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
          </svg>
        </button>
      </div>

      <div className="space-y-6 p-6">
        {/* Descripción */}
        <div>
          <h4 className="mb-1 text-sm font-medium text-gray-500">
            Descripción
          </h4>
          <p className="text-sm text-gray-900">{tarea.descripcion}</p>
        </div>

        {/* Timeline de estados */}
        <div>
          <h4 className="mb-3 text-sm font-medium text-gray-500">
            Timeline
          </h4>
          <div className="flex items-center gap-2">
            {timeline_order.map((estado, i) => {
              const done = i <= idx_actual;
              return (
                <div key={estado} className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={i === idx_actual}
                    onClick={() =>
                      actualizarEstado.mutate({
                        id: tareaId,
                        payload: { nuevo_estado: estado as any },
                      })
                    }
                    className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                      done
                        ? `${estado_colors[estado]} ring-2 ring-offset-1`
                        : "bg-gray-100 text-gray-400"
                    } ${i === idx_actual ? "ring-brand-500" : ""}`}
                  >
                    {estado.replace("_", " ")}
                  </button>
                  {i < timeline_order.length - 1 && (
                    <div
                      className={`h-px w-6 ${done ? "bg-brand-500" : "bg-gray-200"}`}
                    />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Hilo de comentarios */}
        <div>
          <h4 className="mb-3 text-sm font-medium text-gray-500">
            Comentarios ({tarea.comentarios.length})
          </h4>
          <div className="mb-4 max-h-48 space-y-3 overflow-y-auto">
            {tarea.comentarios.length === 0 && (
              <p className="text-sm text-gray-400">
                No hay comentarios todavía.
              </p>
            )}
            {tarea.comentarios.map((c) => (
              <div
                key={c.id}
                className="rounded-lg bg-gray-50 px-4 py-3 text-sm"
              >
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <code className="rounded bg-gray-200 px-1 py-0.5">
                    {c.autor_id.slice(0, 8)}...
                  </code>
                  {c.creado_at && (
                    <span>
                      {new Date(c.creado_at).toLocaleString()}
                    </span>
                  )}
                </div>
                <p className="mt-1 text-gray-700">{c.texto}</p>
              </div>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <Input
              placeholder="Escribí un comentario..."
              value={nuevoComentario}
              onChange={(e) => setNuevoComentario(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleEnviarComentario();
                }
              }}
            />
            <Button
              type="button"
              variant="primary"
              is_loading={agregarComentario.isPending}
              onClick={handleEnviarComentario}
            >
              Enviar
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
