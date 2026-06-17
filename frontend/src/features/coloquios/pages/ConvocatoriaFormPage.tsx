import { useParams, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/shared/components/Button";
import { FormField } from "@/shared/components/FormField";
import { Input } from "@/shared/components/Input";
import { LoadingSpinner } from "@/shared/components/LoadingSpinner";
import {
  useCrearConvocatoria,
  useConvocatoriaById,
  useActualizarConvocatoria,
} from "@/features/coloquios/hooks/useColoquios";
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

const TIPOS_EVALUACION = ["Parcial", "TP", "Coloquio", "Recuperatorio"];

export function ConvocatoriaFormPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEdit = !!id;

  const crearConvocatoria = useCrearConvocatoria();
  const actualizarConvocatoria = useActualizarConvocatoria();
  const convocatoriaQuery = useConvocatoriaById(id ?? "");
  const { data: materias = [] } = useMaterias();
  const { data: cohortes = [] } = useCohortes();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<EvaluacionCreate>({
    resolver: zodResolver(EvaluacionCreateSchema),
    values: isEdit && convocatoriaQuery.data
      ? {
          materia_id: convocatoriaQuery.data.materia_id,
          cohorte_id: convocatoriaQuery.data.cohorte_id,
          tipo: convocatoriaQuery.data.tipo,
          instancia: convocatoriaQuery.data.instancia,
          dias_disponibles: convocatoriaQuery.data.dias_disponibles,
          cupos_por_dia: convocatoriaQuery.data.cupos_por_dia,
          fecha_inicio: convocatoriaQuery.data.fecha_inicio.slice(0, 10),
          fecha_fin: convocatoriaQuery.data.fecha_fin.slice(0, 10),
        }
      : {
          materia_id: "",
          cohorte_id: "",
          tipo: "",
          instancia: "",
          dias_disponibles: 1,
          cupos_por_dia: 1,
          fecha_inicio: "",
          fecha_fin: "",
        },
  });

  const onSubmit = async (data: EvaluacionCreate) => {
    const payload = {
      ...data,
      dias_disponibles: Number(data.dias_disponibles),
      cupos_por_dia: Number(data.cupos_por_dia),
    };

    if (isEdit) {
      await actualizarConvocatoria.mutateAsync({
        id: id!,
        data: {
          instancia: payload.instancia,
          dias_disponibles: payload.dias_disponibles,
          cupos_por_dia: payload.cupos_por_dia,
          fecha_inicio: payload.fecha_inicio,
          fecha_fin: payload.fecha_fin,
        },
      });
    } else {
      await crearConvocatoria.mutateAsync(payload);
    }
    navigate("/coloquios/convocatorias");
  };

  if (isEdit && convocatoriaQuery.isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="h-8 w-8" />
      </div>
    );
  }

  const mutationPending =
    crearConvocatoria.isPending || actualizarConvocatoria.isPending;

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          {isEdit ? "Editar Convocatoria" : "Nueva Convocatoria"}
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          {isEdit
            ? "Actualizá los datos de la convocatoria"
            : "Creá una nueva convocatoria de coloquio"}
        </p>
      </div>

      <form
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-5 rounded-lg border bg-white p-6 shadow-sm"
      >
        {/* Tipo (solo lectura en edición) */}
        <FormField
          label="Tipo"
          html_for="tipo"
          error={errors.tipo?.message}
        >
          <select
            id="tipo"
            className={select_class}
            disabled={isEdit}
            {...register("tipo")}
          >
            <option value="">Seleccionar tipo</option>
            {TIPOS_EVALUACION.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </FormField>

        {/* Instancia */}
        <FormField
          label="Instancia"
          html_for="instancia"
          error={errors.instancia?.message}
        >
          <Input
            id="instancia"
            placeholder="Ej: Coloquio Final - Introducción al Derecho"
            {...register("instancia")}
          />
        </FormField>

        {/* Materia (solo lectura en edición) */}
        <FormField
          label="Materia"
          html_for="materia_id"
          error={errors.materia_id?.message}
        >
          <select
            id="materia_id"
            className={select_class}
            disabled={isEdit}
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

        {/* Cohorte (solo lectura en edición) */}
        <FormField
          label="Cohorte"
          html_for="cohorte_id"
          error={errors.cohorte_id?.message}
        >
          <select
            id="cohorte_id"
            className={select_class}
            disabled={isEdit}
            {...register("cohorte_id")}
          >
            <option value="">Seleccionar cohorte</option>
            {cohortes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
        </FormField>

        {/* Días disponibles */}
        <FormField
          label="Días disponibles"
          html_for="dias_disponibles"
          error={errors.dias_disponibles?.message}
        >
          <Input
            id="dias_disponibles"
            type="number"
            min={1}
            placeholder="Ej: 5"
            {...register("dias_disponibles", { valueAsNumber: true })}
          />
        </FormField>

        {/* Cupos por día */}
        <FormField
          label="Cupos por día"
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

        {/* Fecha inicio */}
        <FormField
          label="Fecha de inicio"
          html_for="fecha_inicio"
          error={errors.fecha_inicio?.message}
        >
          <Input
            id="fecha_inicio"
            type="date"
            {...register("fecha_inicio")}
          />
        </FormField>

        {/* Fecha fin */}
        <FormField
          label="Fecha de fin"
          html_for="fecha_fin"
          error={errors.fecha_fin?.message}
        >
          <Input
            id="fecha_fin"
            type="date"
            {...register("fecha_fin")}
          />
        </FormField>

        <div className="flex items-center gap-3 pt-2">
          <Button type="submit" is_loading={mutationPending}>
            {isEdit ? "Guardar Cambios" : "Crear Convocatoria"}
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => navigate("/coloquios/convocatorias")}
          >
            Cancelar
          </Button>
        </div>
      </form>
    </div>
  );
}
