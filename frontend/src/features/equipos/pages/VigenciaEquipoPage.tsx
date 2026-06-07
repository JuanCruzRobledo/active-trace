import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/shared/components/Button";
import { FormField } from "@/shared/components/FormField";
import { Input } from "@/shared/components/Input";
import { ContextoAcademicoSelector } from "@/shared/components/ContextoAcademicoSelector";
import { useActualizarVigencia } from "@/features/equipos/hooks/useEquipos";
import {
  VigenciaRequestSchema,
  type VigenciaRequest,
} from "@/features/equipos/types/equipos";

export function VigenciaEquipoPage() {
  const actualizarVigencia = useActualizarVigencia();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
  } = useForm<VigenciaRequest>({
    resolver: zodResolver(VigenciaRequestSchema),
    defaultValues: {
      materia_id: "",
      carrera_id: "",
      cohorte_id: "",
      desde: "",
      hasta: "",
    },
  });

  const onSubmit = async (data: VigenciaRequest) => {
    await actualizarVigencia.mutateAsync(data);
    reset();
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-800">
          Actualizar Vigencia
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          Actualizá las fechas de vigencia de todos los equipos en un contexto
          académico
        </p>
      </div>

      <form
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-5 rounded-lg border bg-white p-6 shadow-sm"
      >
        <div className="space-y-3">
          <label className="block text-sm font-medium text-gray-700">
            Contexto académico
          </label>
          <ContextoAcademicoSelector
            onChange={(ctx) => {
              setValue("materia_id", ctx.materiaId);
              setValue("carrera_id", ctx.carreraId);
              setValue("cohorte_id", ctx.cohorteId);
            }}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            label="Nueva fecha de inicio"
            html_for="desde"
            error={errors.desde?.message}
          >
            <Input id="desde" type="date" {...register("desde")} />
          </FormField>

          <FormField
            label="Nueva fecha de fin (opcional)"
            html_for="hasta"
            error={errors.hasta?.message}
          >
            <Input id="hasta" type="date" {...register("hasta")} />
          </FormField>
        </div>

        <div className="flex items-center gap-3 pt-2">
          <Button type="submit" is_loading={actualizarVigencia.isPending}>
            Actualizar vigencia
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              reset();
            }}
          >
            Cancelar
          </Button>
        </div>

        {actualizarVigencia.isSuccess && (
          <div className="rounded-md border border-green-200 bg-green-50 p-4 text-sm text-green-800">
            Vigencia actualizada: {actualizarVigencia.data.afectadas}
            {" "}asignaciones modificadas
          </div>
        )}
      </form>
    </div>
  );
}
