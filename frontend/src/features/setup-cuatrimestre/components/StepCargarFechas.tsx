import { useState } from "react";
import { useForm } from "react-hook-form";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/services/api";
import { Button } from "@/shared/components/Button";
import { Input } from "@/shared/components/Input";
import { FormField } from "@/shared/components/FormField";
import { crearFecha } from "@/features/fechas-academicas/services/fechas-academicas";
import type { CarreraOption } from "@/features/setup-cuatrimestre/types/setup-cuatrimestre";

export function StepCargarFechas({
  cohorte_id,
  on_complete,
  on_skip,
}: {
  cohorte_id: string;
  on_complete: () => void;
  on_skip: () => void;
}) {
  const [loading, set_loading] = useState(false);
  const [materia_id, set_materia_id] = useState("");

  const materias_query = useQuery({
    queryKey: ["materias", cohorte_id],
    queryFn: () => api.get<CarreraOption[]>(`/cohortes/${cohorte_id}/materias`).then((r) => r.data),
    enabled: !!cohorte_id,
  });

  const form = useForm({
    defaultValues: { tipo: "parcial", titulo: "", fecha_evaluacion: "" },
  });

  const handle_submit = form.handleSubmit(async (values) => {
    if (!materia_id) return;
    set_loading(true);
    try {
      await crearFecha({ ...values, materia_id, cohorte_id });
      on_complete();
    } finally {
      set_loading(false);
    }
  });

  return (
    <form onSubmit={handle_submit} className="space-y-4 rounded-lg border bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900">Cargar fechas de evaluación</h2>
      <p className="text-sm text-gray-500">Registrá las fechas de evaluación para las materias.</p>
      <div className="grid gap-4 sm:grid-cols-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Materia</label>
          <select
            value={materia_id}
            onChange={(e) => set_materia_id(e.target.value)}
            className="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">Seleccionar</option>
            {(materias_query.data ?? []).map((m) => (
              <option key={m.id} value={m.id}>
                {m.nombre}
              </option>
            ))}
          </select>
        </div>
        <FormField label="Título" html_for="f-titulo">
          <Input id="f-titulo" {...form.register("titulo", { required: true })} />
        </FormField>
        <FormField label="Tipo" html_for="f-tipo">
          <select
            id="f-tipo"
            {...form.register("tipo")}
            className="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="parcial">Parcial</option>
            <option value="final">Final</option>
            <option value="tp">TP</option>
            <option value="recuperatorio">Recuperatorio</option>
          </select>
        </FormField>
        <FormField label="Fecha" html_for="f-fecha">
          <Input id="f-fecha" type="datetime-local" {...form.register("fecha_evaluacion", { required: true })} />
        </FormField>
      </div>
      <div className="flex justify-between">
        <Button variant="ghost" onClick={on_skip} type="button">
          Saltar este paso
        </Button>
        <Button type="submit" is_loading={loading}>
          Guardar fecha
        </Button>
      </div>
    </form>
  );
}
