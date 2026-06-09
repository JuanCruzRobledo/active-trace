import { type UseFormRegister, type FieldErrors, type UseFormWatch } from "react-hook-form";
import { Button } from "@/shared/components/Button";
import { FormField } from "@/shared/components/FormField";
import { Input } from "@/shared/components/Input";
import type { AvisoCreate } from "@/features/avisos/types/avisos";
import type { Materia, Cohorte } from "@/features/estructura-academica/types/estructura";

const input_class =
  "block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500";

const select_class =
  "block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500";

interface AvisoFormBodyProps {
  register: UseFormRegister<AvisoCreate>;
  errors: FieldErrors<AvisoCreate>;
  watch: UseFormWatch<AvisoCreate>;
  isEdit: boolean;
  isPending: boolean;
  onSubmit: (e: React.FormEvent) => void;
  onCancel: () => void;
  materias?: Materia[];
  cohortes?: Cohorte[];
}

export function AvisoFormBody({
  register,
  errors,
  watch,
  isEdit,
  isPending,
  onSubmit,
  onCancel,
  materias = [],
  cohortes = [],
}: AvisoFormBodyProps) {
  const alcance = watch("alcance");

  return (
    <form onSubmit={onSubmit}
      className="space-y-5 rounded-lg border bg-white p-6 shadow-sm"
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField
          label="Alcance"
          html_for="alcance"
          error={errors.alcance?.message}
        >
          <select
            id="alcance"
            className={select_class}
            {...register("alcance")}
          >
            <option value="Global">Global</option>
            <option value="PorMateria">Por Materia</option>
            <option value="PorCohorte">Por Cohorte</option>
            <option value="PorRol">Por Rol</option>
          </select>
        </FormField>

        <FormField
          label="Severidad"
          html_for="severidad"
          error={errors.severidad?.message}
        >
          <select
            id="severidad"
            className={select_class}
            {...register("severidad")}
          >
            <option value="Info">Info</option>
            <option value="Advertencia">Advertencia</option>
            <option value="Crítico">Crítico</option>
          </select>
        </FormField>
      </div>

      {alcance === "PorMateria" && (
        <FormField label="Materia" html_for="materia_id" error={errors.materia_id?.message}>
          <select id="materia_id" className={select_class} {...register("materia_id")}>
            <option value="">Seleccionar materia</option>
            {materias.map((m) => (
              <option key={m.id} value={m.id}>{m.nombre}</option>
            ))}
          </select>
        </FormField>
      )}
      {alcance === "PorCohorte" && (
        <FormField label="Cohorte" html_for="cohorte_id" error={errors.cohorte_id?.message}>
          <select id="cohorte_id" className={select_class} {...register("cohorte_id")}>
            <option value="">Seleccionar cohorte</option>
            {cohortes.map((c) => (
              <option key={c.id} value={c.id}>{c.nombre}</option>
            ))}
          </select>
        </FormField>
      )}
      {alcance === "PorRol" && (
        <FormField label="Rol destino" html_for="rol_destino" error={errors.rol_destino?.message}>
          <select id="rol_destino" className={select_class} {...register("rol_destino")}>
            <option value="">Seleccionar rol</option>
            <option value="profesor">Profesor</option>
            <option value="tutor">Tutor</option>
            <option value="coordinador">Coordinador</option>
            <option value="nexo">Nexo</option>
          </select>
        </FormField>
      )}

      <FormField
        label="Título"
        html_for="titulo"
        error={errors.titulo?.message}
      >
        <Input
          id="titulo"
          placeholder="Título del aviso"
          {...register("titulo")}
        />
      </FormField>

      <FormField
        label="Cuerpo"
        html_for="cuerpo"
        error={errors.cuerpo?.message}
      >
        <textarea
          id="cuerpo"
          rows={4}
          className={input_class}
          placeholder="Contenido del aviso"
          {...register("cuerpo")}
        />
      </FormField>

      <div className="grid gap-4 sm:grid-cols-2">
        <FormField
          label="Inicio"
          html_for="inicio_en"
          error={errors.inicio_en?.message}
        >
          <Input
            id="inicio_en"
            type="date"
            {...register("inicio_en")}
          />
        </FormField>

        <FormField
          label="Fin"
          html_for="fin_en"
          error={errors.fin_en?.message}
        >
          <Input
            id="fin_en"
            type="date"
            {...register("fin_en")}
          />
        </FormField>
      </div>

      <FormField
        label="Orden"
        html_for="orden"
        error={errors.orden?.message}
      >
        <Input
          id="orden"
          type="number"
          {...register("orden", { valueAsNumber: true })}
        />
      </FormField>

      <div className="flex items-center gap-2">
        <input
          id="requiere_ack"
          type="checkbox"
          className="h-4 w-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
          {...register("requiere_ack")}
        />
        <label htmlFor="requiere_ack" className="text-sm text-gray-700">
          Requiere confirmación (acknowledge)
        </label>
      </div>

      <div className="flex items-center gap-3 pt-2">
        <Button type="submit" is_loading={isPending}>
          {isEdit ? "Guardar cambios" : "Crear aviso"}
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}
