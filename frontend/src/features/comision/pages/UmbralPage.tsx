import { useState, useEffect } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { Button } from "@/shared/components/Button";
import { Input } from "@/shared/components/Input";
import { FormField } from "@/shared/components/FormField";
import { LoadingSpinner } from "@/shared/components/LoadingSpinner";
import { ErrorMessage } from "@/shared/components/ErrorMessage";
import {
  useUmbralMateria,
  useUpdateUmbral,
} from "@/features/comision/hooks/useUmbralMateria";

export function UmbralPage() {
  const { materiaId } = useParams<{ materiaId: string }>();
  const [searchParams] = useSearchParams();
  const asignacionId = searchParams.get("asignacion_id") ?? "";
  const { data, isLoading, isError, error } = useUmbralMateria(materiaId!, asignacionId);
  const updateMutation = useUpdateUmbral(materiaId!, asignacionId);
  const [porcentaje, setPorcentaje] = useState<number>(60);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    if (data) {
      setPorcentaje(data.umbral_pct);
    }
  }, [data]);

  const handleSave = () => {
    setValidationError(null);
    setSuccessMsg(null);
    if (porcentaje < 0 || porcentaje > 100) {
      setValidationError("El porcentaje debe estar entre 0 y 100.");
      return;
    }
    updateMutation.mutate(porcentaje, {
      onSuccess: () => {
        setSuccessMsg("Umbral actualizado correctamente.");
      },
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="h-8 w-8" />
      </div>
    );
  }

  if (isError) {
    return (
      <ErrorMessage
        message={error?.message ?? "Error al cargar el umbral."}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Umbral de aprobación
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Configurá el porcentaje mínimo de actividades aprobadas para
          considerar a un alumno como "al día"
        </p>
      </div>

      {successMsg && (
        <div
          className="rounded-md border border-green-200 bg-green-50 p-4 text-sm text-green-800"
          role="alert"
        >
          {successMsg}
        </div>
      )}

      <div className="max-w-md rounded-lg border bg-white p-6 shadow-sm">
        <div className="space-y-4">
          <FormField
            label="Porcentaje mínimo (%)"
            html_for="umbral-input"
            error={validationError ?? undefined}
            hint="Valor entre 0 y 100. Por defecto: 60%"
          >
            <Input
              id="umbral-input"
              type="number"
              min={0}
              max={100}
              value={porcentaje}
              onChange={(e) => {
                setPorcentaje(Number(e.target.value));
                setValidationError(null);
                setSuccessMsg(null);
              }}
              has_error={!!validationError}
            />
          </FormField>

          <Button
            onClick={handleSave}
            is_loading={updateMutation.isPending}
            disabled={updateMutation.isPending}
          >
            Guardar
          </Button>
        </div>
      </div>

      {updateMutation.isError && (
        <ErrorMessage
          message={
            updateMutation.error?.message ??
            "Error al actualizar el umbral."
          }
        />
      )}
    </div>
  );
}
