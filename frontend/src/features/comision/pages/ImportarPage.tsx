import { useState, useRef } from "react";
import { useParams } from "react-router-dom";
import { Button } from "@/shared/components/Button";
import { ErrorMessage } from "@/shared/components/ErrorMessage";
import {
  usePreviewCalificaciones,
  useImportarCalificaciones,
} from "@/features/comision/hooks/useImportarCalificaciones";
import type { PreviewRow } from "@/features/comision/services/calificaciones";

export function ImportarPage() {
  const { materiaId } = useParams<{ materiaId: string }>();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [selectedActividades, setSelectedActividades] = useState<string[]>([]);
  const [successSummary, setSuccessSummary] = useState<string | null>(null);
  const [previewToken, setPreviewToken] = useState<string>("");

  const previewMutation = usePreviewCalificaciones(materiaId!);
  const importMutation = useImportarCalificaciones(materiaId!, previewToken);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    setSuccessSummary(null);
  };

  const handlePreview = () => {
    if (!file) return;
    setSuccessSummary(null);
    previewMutation.mutate(file, {
      onSuccess: (data) => {
        setPreviewToken(data.preview_token);
      },
    });
  };

  const handleConfirm = () => {
    if (!previewMutation.data) return;
    const acts =
      selectedActividades.length > 0
        ? selectedActividades
        : previewMutation.data.actividades;
    importMutation.mutate(acts, {
      onSuccess: (result) => {
        setSuccessSummary(
          `Importación completada: ${result.importadas} filas importadas` +
            (result.errores > 0 ? `, ${result.errores} errores` : "") +
            ".",
        );
        previewMutation.reset();
        setPreviewToken("");
        setSelectedActividades([]);
        setFile(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
      },
    });
  };

  const toggleActividad = (act: string) => {
    setSelectedActividades((prev) =>
      prev.includes(act)
        ? prev.filter((a) => a !== act)
        : [...prev, act],
    );
  };

  const previewData = previewMutation.data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Importar Calificaciones
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Cargá un archivo CSV o Excel con las calificaciones de los alumnos
        </p>
      </div>

      {successSummary && (
        <div
          className="rounded-md border border-green-200 bg-green-50 p-4 text-sm text-green-800"
          role="alert"
        >
          {successSummary}
        </div>
      )}

      <div className="rounded-lg border bg-white p-6 shadow-sm">
        <div className="space-y-4">
          <div>
            <label
              htmlFor="file-upload"
              className="mb-1 block text-sm font-medium text-gray-700"
            >
              Archivo de calificaciones
            </label>
            <input
              ref={fileInputRef}
              id="file-upload"
              type="file"
              accept=".csv,.xlsx,.xls"
              onChange={handleFileChange}
              className="block w-full text-sm text-gray-500 file:mr-4 file:rounded-md file:border-0 file:bg-brand-50 file:px-4 file:py-2 file:text-sm file:font-medium file:text-brand-700 hover:file:bg-brand-100"
            />
          </div>

          <Button
            onClick={handlePreview}
            disabled={!file || previewMutation.isPending}
            is_loading={previewMutation.isPending}
          >
            Previsualizar
          </Button>
        </div>
      </div>

      {previewMutation.isError && (
        <ErrorMessage
          message={
            previewMutation.error?.message ??
            "Error al procesar el archivo. Verificá el formato e intentá de nuevo."
          }
          action_label="Reintentar"
          on_action={handlePreview}
        />
      )}

      {previewData && (
        <div className="space-y-4">
          <div className="rounded-lg border bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold text-gray-900">
              Vista previa ({previewData.total_filas} filas)
            </h2>

            {previewData.actividades.length > 0 && (
              <div className="mb-4">
                <p className="mb-2 text-sm font-medium text-gray-700">
                  Seleccionar actividades a importar:
                </p>
                <div className="flex flex-wrap gap-3">
                  {previewData.actividades.map((act) => (
                    <label
                      key={act}
                      className="flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm"
                    >
                      <input
                        type="checkbox"
                        checked={selectedActividades.includes(act)}
                        onChange={() => toggleActividad(act)}
                        className="h-4 w-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
                      />
                      {act}
                    </label>
                  ))}
                </div>
              </div>
            )}

            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium text-gray-500">
                      Alumno
                    </th>
                    <th className="px-4 py-2 text-left font-medium text-gray-500">
                      Legajo
                    </th>
                    <th className="px-4 py-2 text-left font-medium text-gray-500">
                      Actividad
                    </th>
                    <th className="px-4 py-2 text-right font-medium text-gray-500">
                      Nota
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {previewData.filas.map((row: PreviewRow, i: number) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-2">{row.alumno}</td>
                      <td className="px-4 py-2 text-gray-500">{row.legajo}</td>
                      <td className="px-4 py-2">{row.actividad}</td>
                      <td className="px-4 py-2 text-right">{row.nota}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="flex gap-3">
            <Button
              onClick={handleConfirm}
              is_loading={importMutation.isPending}
            >
              Confirmar importación
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                previewMutation.reset();
                setSelectedActividades([]);
              }}
            >
              Cancelar
            </Button>
          </div>

          {importMutation.isError && (
            <ErrorMessage
              message={
                importMutation.error?.message ??
                "Error al importar. Intentalo de nuevo."
              }
            />
          )}
        </div>
      )}
    </div>
  );
}
