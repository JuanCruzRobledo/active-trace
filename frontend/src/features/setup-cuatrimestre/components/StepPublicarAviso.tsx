import { useState } from "react";
import { useForm } from "react-hook-form";
import { api } from "@/shared/services/api";
import { Button } from "@/shared/components/Button";
import { Input } from "@/shared/components/Input";
import { FormField } from "@/shared/components/FormField";

export function StepPublicarAviso({
  cohorte_id,
  on_complete,
  on_skip,
}: {
  cohorte_id: string;
  on_complete: () => void;
  on_skip: () => void;
}) {
  const [loading, set_loading] = useState(false);

  const form = useForm({
    defaultValues: {
      titulo: "¡Bienvenidos al nuevo cuatrimestre!",
      contenido: "",
      dirigido_a: "alumnos",
    },
  });

  const handle_submit = form.handleSubmit(async (values) => {
    set_loading(true);
    try {
      await api.post("/avisos", { ...values, cohorte_id });
      on_complete();
    } finally {
      set_loading(false);
    }
  });

  return (
    <form onSubmit={handle_submit} className="space-y-4 rounded-lg border bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900">Publicar aviso de bienvenida</h2>
      <p className="text-sm text-gray-500">Informá a los alumnos sobre el inicio del cuatrimestre.</p>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Título" html_for="a-titulo">
          <Input id="a-titulo" {...form.register("titulo", { required: true })} />
        </FormField>
        <FormField label="Dirigido a" html_for="a-dirigido">
          <select
            id="a-dirigido"
            {...form.register("dirigido_a")}
            className="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="alumnos">Alumnos</option>
            <option value="docentes">Docentes</option>
            <option value="todos">Todos</option>
          </select>
        </FormField>
        <div className="sm:col-span-2">
          <FormField label="Contenido" html_for="a-contenido">
            <textarea
              id="a-contenido"
              rows={4}
              {...form.register("contenido", { required: true })}
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </FormField>
        </div>
      </div>
      <div className="flex justify-between">
        <Button variant="ghost" onClick={on_skip} type="button">
          Saltar este paso
        </Button>
        <Button type="submit" is_loading={loading}>
          Publicar aviso
        </Button>
      </div>
    </form>
  );
}
