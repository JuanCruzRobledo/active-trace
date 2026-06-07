import { useState, useCallback } from "react";
import { Button } from "@/shared/components/Button";
import { ContextoAcademicoSelector } from "@/shared/components/ContextoAcademicoSelector";
import { useExportarEquipo } from "@/features/equipos/hooks/useEquipos";

export function ExportarEquipoPage() {
  const [contexto, setContexto] = useState<{
    carreraId: string;
    cohorteId: string;
    materiaId: string;
  } | null>(null);

  const exportarEquipo = useExportarEquipo();

  const handleExport = useCallback(() => {
    if (!contexto) return;
    exportarEquipo.mutate(
      {
        materia_id: contexto.materiaId,
        carrera_id: contexto.carreraId,
        cohorte_id: contexto.cohorteId,
      },
      {
        onSuccess: (blob) => {
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `equipos-${contexto.materiaId.slice(0, 8)}.csv`;
          a.click();
          URL.revokeObjectURL(url);
        },
      },
    );
  }, [contexto, exportarEquipo]);

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-800">
          Exportar Equipos
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          Descargá un archivo CSV con los equipos docentes de un contexto
          académico
        </p>
      </div>

      <div className="space-y-5 rounded-lg border bg-white p-6 shadow-sm">
        <div className="space-y-3">
          <label className="block text-sm font-medium text-gray-700">
            Contexto académico
          </label>
          <ContextoAcademicoSelector
            onChange={(ctx) => setContexto(ctx)}
          />
        </div>

        <div className="flex items-center gap-3 pt-2">
          <Button
            type="button"
            onClick={handleExport}
            disabled={!contexto}
            is_loading={exportarEquipo.isPending}
          >
            Exportar CSV
          </Button>
        </div>

        {exportarEquipo.isSuccess && (
          <div className="rounded-md border border-green-200 bg-green-50 p-4 text-sm text-green-800">
            Archivo exportado exitosamente
          </div>
        )}
      </div>
    </div>
  );
}
