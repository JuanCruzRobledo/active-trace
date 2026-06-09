import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/shared/components/Button";
import { FormField } from "@/shared/components/FormField";
import { Input } from "@/shared/components/Input";
import { ContextoAcademicoSelector } from "@/shared/components/ContextoAcademicoSelector";
import { useClonarEquipo } from "@/features/equipos/hooks/useEquipos";
import {
  ClonarEquipoRequestSchema,
  type ClonarEquipoRequest,
} from "@/features/equipos/types/equipos";

export function ClonarEquipoPage() {
  const clonarEquipo = useClonarEquipo();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
  } = useForm<ClonarEquipoRequest>({
    resolver: zodResolver(ClonarEquipoRequestSchema),
    defaultValues: {
      origen_materia_id: "",
      origen_carrera_id: "",
      origen_cohorte_id: "",
      destino_materia_id: "",
      destino_carrera_id: "",
      destino_cohorte_id: "",
      destino_desde: "",
      destino_hasta: "",
    },
  });

  const onSubmit = async (data: ClonarEquipoRequest) => {
    // Convertir string vacio a null para que Pydantic no falle con datetime
    const payload = {
      ...data,
      destino_hasta: data.destino_hasta || undefined,
    };
    await clonarEquipo.mutateAsync(payload);
    reset();
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-800">Clonar Equipo</h2>
        <p className="mt-1 text-sm text-gray-500">
          Cloná una configuración de equipo de un contexto académico a otro
        </p>
      </div>

      <form
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-5 rounded-lg border bg-white p-6 shadow-sm"
      >
        <fieldset className="space-y-3">
          <legend className="text-sm font-semibold text-gray-800">Origen</legend>
          <ContextoAcademicoSelector
            onChange={(ctx) => {
              setValue("origen_materia_id", ctx.materiaId);
              setValue("origen_carrera_id", ctx.carreraId);
              setValue("origen_cohorte_id", ctx.cohorteId);
            }}
          />
        </fieldset>

        <hr className="border-gray-200" />

        <fieldset className="space-y-3">
          <legend className="text-sm font-semibold text-gray-800">Destino</legend>
          <ContextoAcademicoSelector
            onChange={(ctx) => {
              setValue("destino_materia_id", ctx.materiaId);
              setValue("destino_carrera_id", ctx.carreraId);
              setValue("destino_cohorte_id", ctx.cohorteId);
            }}
          />
        </fieldset>

        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            label="Inicio en destino"
            html_for="destino_desde"
            error={errors.destino_desde?.message}
          >
            <Input
              id="destino_desde"
              type="date"
              {...register("destino_desde")}
            />
          </FormField>

          <FormField
            label="Fin en destino (opcional)"
            html_for="destino_hasta"
            error={errors.destino_hasta?.message}
          >
            <Input
              id="destino_hasta"
              type="date"
              {...register("destino_hasta")}
            />
          </FormField>
        </div>

        <div className="flex items-center gap-3 pt-2">
          <Button type="submit" is_loading={clonarEquipo.isPending}>
            Clonar
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

        {clonarEquipo.isSuccess && (
          <div className="rounded-md border border-green-200 bg-green-50 p-4 text-sm text-green-800">
            Equipo clonado exitosamente: {clonarEquipo.data.creadas} asignaciones
            creadas de &ldquo;{clonarEquipo.data.origen}&rdquo; a
            &ldquo;{clonarEquipo.data.destino}&rdquo;
          </div>
        )}

        {clonarEquipo.isError && (
          <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            {clonarEquipo.error instanceof Error
              ? clonarEquipo.error.message
              : "Error al clonar el equipo. Verificá que el contexto origen tenga asignaciones."}
          </div>
        )}
      </form>
    </div>
  );
}
