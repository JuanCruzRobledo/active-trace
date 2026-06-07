import { useState } from "react";
import { useForm } from "react-hook-form";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/services/api";
import { Button } from "@/shared/components/Button";
import { Input } from "@/shared/components/Input";
import { FormField } from "@/shared/components/FormField";
import { crearCohorte } from "@/features/setup-cuatrimestre/services/setup-cuatrimestre";
import type { CohorteInput } from "@/features/setup-cuatrimestre/services/setup-cuatrimestre";
import type { CarreraOption } from "@/features/setup-cuatrimestre/types/setup-cuatrimestre";

export function StepCrearCohorte({
  on_complete,
}: {
  on_complete: (cohorte_id: string) => void;
}) {
  const [loading, set_loading] = useState(false);

  const carreras_query = useQuery({
    queryKey: ["carreras"],
    queryFn: () => api.get<CarreraOption[]>("/carreras").then((r) => r.data),
  });

  const form = useForm<CohorteInput>({
    defaultValues: {
      nombre: "",
      anio: new Date().getFullYear(),
      fecha_inicio: "",
      fecha_fin: "",
      carrera_id: "",
    },
  });

  const handle_submit = form.handleSubmit(async (values) => {
    set_loading(true);
    try {
      const result = await crearCohorte(values);
      on_complete(result.id);
    } finally {
      set_loading(false);
    }
  });

  return (
    <form onSubmit={handle_submit} className="space-y-4 rounded-lg border bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900">Crear nueva cohorte</h2>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Carrera" html_for="carrera_id" error={form.formState.errors.carrera_id?.message}>
          <select
            id="carrera_id"
            {...form.register("carrera_id", { required: true })}
            className="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">Seleccionar carrera</option>
            {(carreras_query.data ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Nombre" html_for="nombre" error={form.formState.errors.nombre?.message}>
          <Input id="nombre" {...form.register("nombre", { required: true })} placeholder="Ej: 2026 1C" />
        </FormField>
        <FormField label="Año" html_for="anio" error={form.formState.errors.anio?.message}>
          <Input id="anio" type="number" {...form.register("anio", { valueAsNumber: true })} />
        </FormField>
        <FormField label="Fecha inicio" html_for="fecha_inicio" error={form.formState.errors.fecha_inicio?.message}>
          <Input id="fecha_inicio" type="date" {...form.register("fecha_inicio", { required: true })} />
        </FormField>
        <FormField label="Fecha fin" html_for="fecha_fin" error={form.formState.errors.fecha_fin?.message}>
          <Input id="fecha_fin" type="date" {...form.register("fecha_fin", { required: true })} />
        </FormField>
      </div>
      <div className="flex justify-end">
        <Button type="submit" is_loading={loading}>
          Crear cohorte
        </Button>
      </div>
    </form>
  );
}
