import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router-dom";
import { Button } from "@/shared/components/Button";
import { FormField } from "@/shared/components/FormField";
import { Input } from "@/shared/components/Input";
import { useCrearConvocatoria } from "@/features/coloquios/hooks/useColoquios";
import {
  EvaluacionCreateSchema,
  type EvaluacionCreate,
} from "@/features/coloquios/types/coloquios";

export function ConvocatoriaFormPage() {
  const navigate = useNavigate();
  const crearConvocatoria = useCrearConvocatoria();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<EvaluacionCreate>({
    resolver: zodResolver(EvaluacionCreateSchema),
    defaultValues: {
      materia_id: "",
      titulo: "",
      cohorte_id: undefined,
      cupos_por_dia: undefined,
    },
  });

  const onSubmit = async (data: EvaluacionCreate) => {
    await crearConvocatoria.mutateAsync(data);
    navigate("/coloquios/convocatorias");
  };

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Nueva Convocatoria
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Creá una nueva convocatoria de coloquio
        </p>
      </div>

      <form
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-5 rounded-lg border bg-white p-6 shadow-sm"
      >
        <FormField
          label="Título"
          html_for="titulo"
          error={errors.titulo?.message}
        >
          <Input
            id="titulo"
            placeholder="Ej: Coloquio Final - Introducción al Derecho"
            {...register("titulo")}
          />
        </FormField>

        <FormField
          label="Materia (UUID)"
          html_for="materia_id"
          error={errors.materia_id?.message}
        >
          <Input
            id="materia_id"
            placeholder="UUID de la materia"
            {...register("materia_id")}
          />
        </FormField>

        <FormField
          label="Cohorte (UUID, opcional)"
          html_for="cohorte_id"
          error={errors.cohorte_id?.message}
        >
          <Input
            id="cohorte_id"
            placeholder="UUID del cohorte"
            {...register("cohorte_id")}
          />
        </FormField>

        <FormField
          label="Cupos por día (opcional)"
          html_for="cupos_por_dia"
          error={errors.cupos_por_dia?.message}
        >
          <Input
            id="cupos_por_dia"
            type="number"
            min={1}
            placeholder="Ej: 30"
            {...register("cupos_por_dia", { valueAsNumber: true })}
          />
        </FormField>

        <div className="flex items-center gap-3 pt-2">
          <Button type="submit" is_loading={crearConvocatoria.isPending}>
            Crear Convocatoria
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => navigate("/coloquios")}
          >
            Cancelar
          </Button>
        </div>
      </form>
    </div>
  );
}
