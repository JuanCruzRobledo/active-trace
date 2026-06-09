import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/shared/components/Button";
import { FormField } from "@/shared/components/FormField";
import { Input } from "@/shared/components/Input";
import { ContextoAcademicoSelector } from "@/shared/components/ContextoAcademicoSelector";
import { useAsignacionMasiva } from "@/features/equipos/hooks/useEquipos";
import {
  AsignacionMasivaRequestSchema,
  type AsignacionMasivaRequest,
} from "@/features/equipos/types/equipos";
import { useUsuariosTenant } from "@/features/usuarios-tenant/hooks/useUsuariosTenant";

const ROLES_DOCENTES = [
  { value: "PROFESOR", label: "Profesor" },
  { value: "TUTOR", label: "Tutor" },
  { value: "COORDINADOR", label: "Coordinador" },
  { value: "NEXO", label: "Nexo" },
];

const select_class =
  "block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500";

export function AsignacionMasivaPage() {
  const asignacionMasiva = useAsignacionMasiva();
  const { data: usuarios = [] } = useUsuariosTenant();

  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
  } = useForm<AsignacionMasivaRequest>({
    resolver: zodResolver(AsignacionMasivaRequestSchema),
    defaultValues: {
      usuario_ids: [],
      materia_id: "",
      carrera_id: "",
      cohorte_id: "",
      rol: "",
      desde: "",
      hasta: "",
    },
  });

  const onSubmit = async (data: AsignacionMasivaRequest) => {
    await asignacionMasiva.mutateAsync(data);
    reset();
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-800">
          Asignación Masiva
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          Asigná múltiples docentes a una materia, carrera y cohorte
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

        <FormField
          label="Docentes"
          html_for="usuario_ids"
          error={errors.usuario_ids?.message}
        >
          <Controller
            name="usuario_ids"
            control={control}
            render={({ field }) => (
              <select
                id="usuario_ids"
                multiple
                size={6}
                className={select_class}
                value={field.value}
                onChange={(e) => {
                  field.onChange(
                    Array.from(e.target.selectedOptions, (o) => o.value)
                  );
                }}
              >
                {usuarios
                  .slice()
                  .sort((a, b) =>
                    `${a.apellidos} ${a.nombre}`.localeCompare(
                      `${b.apellidos} ${b.nombre}`
                    )
                  )
                  .map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.apellidos}, {u.nombre} — {u.email}
                    </option>
                  ))}
              </select>
            )}
          />
          <p className="mt-1 text-xs text-gray-500">
            Ctrl+clic (o Cmd+clic) para seleccionar varios
          </p>
        </FormField>

        <FormField label="Rol" html_for="rol" error={errors.rol?.message}>
          <select id="rol" className={select_class} {...register("rol")}>
            <option value="">Seleccionar rol</option>
            {ROLES_DOCENTES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </FormField>

        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            label="Desde"
            html_for="desde"
            error={errors.desde?.message}
          >
            <Input id="desde" type="date" {...register("desde")} />
          </FormField>

          <FormField
            label="Hasta (opcional)"
            html_for="hasta"
            error={errors.hasta?.message}
          >
            <Input id="hasta" type="date" {...register("hasta")} />
          </FormField>
        </div>

        <div className="flex items-center gap-3 pt-2">
          <Button type="submit" is_loading={asignacionMasiva.isPending}>
            Asignar
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => reset()}
          >
            Cancelar
          </Button>
        </div>

        {asignacionMasiva.isSuccess && (
          <div className="rounded-md border border-green-200 bg-green-50 p-4 text-sm text-green-800">
            Asignación masiva completada exitosamente
          </div>
        )}
      </form>
    </div>
  );
}
