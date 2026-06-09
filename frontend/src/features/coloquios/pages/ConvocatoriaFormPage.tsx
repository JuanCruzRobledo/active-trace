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
import {
  useMaterias,
  useCohortes,
} from "@/features/estructura-academica/hooks/useEstructura";

const select_class =
  "block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500";

export function ConvocatoriaFormPage() {
  const navigate = useNavigate();
  const crearConvocatoria = useCrearConvocatoria();
  const { data: materias = [] } = useMaterias();
  const { data: cohortes = [] } = useCohortes();

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
          label="Materia"
          html_for="materia_id"
          error={errors.materia_id?.message}
        >
          <select
            id="materia_id"
            className={select_class}
            {...register("materia_id")}
          >
            <option value="">Seleccionar materia</option>
            {materias.map((m) => (
              <option key={m.id} value={m.id}>
                {m.nombre}
              </option>
            ))}
          </select>
        </FormField>

        <FormField
          label="Cohorte (opcional)"
          html_for="cohorte_id"
          error={errors.cohorte_id?.message}
        >
          <select
            id="cohorte_id"
            className={select_class}
            {...register("cohorte_id")}
          >
            <option value="">Sin cohorte específico</option>
            {cohortes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
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
