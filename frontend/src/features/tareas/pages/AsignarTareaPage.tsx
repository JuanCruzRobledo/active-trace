import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router-dom";
import { Button } from "@/shared/components/Button";
import { FormField } from "@/shared/components/FormField";
import { useCrearTarea, useDocentes } from "@/features/tareas/hooks/useTareas";
import {
  TareaCreateSchema,
  type TareaCreate,
} from "@/features/tareas/types/tareas";
import { useMaterias } from "@/features/estructura-academica/hooks/useEstructura";

const select_class =
  "block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500";

export function AsignarTareaPage() {
  const navigate = useNavigate();
  const crearTarea = useCrearTarea();
  const { data: docentes = [] } = useDocentes();
  const { data: materias = [] } = useMaterias();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<TareaCreate>({
    resolver: zodResolver(TareaCreateSchema),
    defaultValues: {
      asignado_a: "",
      descripcion: "",
      materia_id: undefined,
    },
  });

  const onSubmit = async (data: TareaCreate) => {
    await crearTarea.mutateAsync(data);
    navigate("/tareas/mis-tareas");
  };

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Asignar Tarea</h1>
        <p className="mt-1 text-sm text-gray-500">
          Creá una nueva tarea para un docente
        </p>
      </div>

      <form
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-5 rounded-lg border bg-white p-6 shadow-sm"
      >
        <FormField
          label="Docente"
          html_for="asignado_a"
          error={errors.asignado_a?.message}
        >
          <select
            id="asignado_a"
            className={select_class}
            {...register("asignado_a")}
          >
            <option value="">Seleccionar docente</option>
            {docentes.map((d) => (
              <option key={d.id} value={d.id}>
                {d.apellidos}, {d.nombre}
              </option>
            ))}
          </select>
        </FormField>

        <FormField
          label="Materia (opcional)"
          html_for="materia_id"
          error={errors.materia_id?.message}
        >
          <select
            id="materia_id"
            className={select_class}
            {...register("materia_id")}
          >
            <option value="">Sin materia específica</option>
            {materias
              .filter((m) => m.estado !== "Inactivo")
              .map((m) => (
                <option key={m.id} value={m.id}>
                  {m.nombre}
                </option>
              ))}
          </select>
        </FormField>

        <FormField
          label="Descripción"
          html_for="descripcion"
          error={errors.descripcion?.message}
        >
          <textarea
            id="descripcion"
            rows={4}
            className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm transition-colors focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
            placeholder="Describí la tarea a realizar..."
            {...register("descripcion")}
          />
        </FormField>

        <div className="flex items-center gap-3 pt-2">
          <Button type="submit" is_loading={crearTarea.isPending}>
            Asignar Tarea
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => navigate("/tareas")}
          >
            Cancelar
          </Button>
        </div>
      </form>
    </div>
  );
}
