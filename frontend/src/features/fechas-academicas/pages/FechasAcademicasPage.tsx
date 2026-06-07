import { useState } from "react";
import { useForm } from "react-hook-form";
import { FilterableTable, type Column } from "@/shared/components/FilterableTable";
import { ContextoAcademicoSelector } from "@/shared/components/ContextoAcademicoSelector";
import { Button } from "@/shared/components/Button";
import { Input } from "@/shared/components/Input";
import { FormField } from "@/shared/components/FormField";
import { ConfirmDialog } from "@/shared/components/ConfirmDialog";
import {
  useFechasAcademicas,
  useCrearFecha,
  useActualizarFecha,
  useEliminarFecha,
} from "@/features/fechas-academicas/hooks/useFechasAcademicas";
import { exportarLMS } from "@/features/fechas-academicas/services/fechas-academicas";
import type { FechaAcademica, FechaAcademicaCreate, FechaAcademicaFilters } from "@/features/fechas-academicas/types/fechas-academicas";

const tipos = ["parcial", "final", "tp", "recuperatorio", "coloquio", "otro"];

const columns: Column<FechaAcademica>[] = [
  { key: "titulo", label: "Título", sortable: true },
  { key: "tipo", label: "Tipo", sortable: true },
  { key: "fecha_evaluacion", label: "Fecha", sortable: true },
  { key: "numero_instancia", label: "N° instancia", sortable: true },
];

export function FechasAcademicasPage() {
  const [contexto, set_contexto] = useState({ carreraId: "", cohorteId: "", materiaId: "" });
  const [filters] = useState<FechaAcademicaFilters>({});
  const [show_form, set_show_form] = useState(false);
  const [editing_id, set_editing_id] = useState<string | null>(null);
  const [delete_id, set_delete_id] = useState<string | null>(null);
  const [export_loading, set_export_loading] = useState(false);

  const query_filters = { ...filters, materia_id: filters.materia_id || contexto.materiaId || undefined };
  const { data, isLoading, error } = useFechasAcademicas(query_filters);
  const crear_mutation = useCrearFecha();
  const actualizar_mutation = useActualizarFecha();
  const eliminar_mutation = useEliminarFecha();

  const form = useForm<FechaAcademicaCreate>({
    defaultValues: { materia_id: "", tipo: "parcial", titulo: "", fecha_evaluacion: "", numero_instancia: null },
  });

  const items = data?.items ?? [];

  const handle_submit = form.handleSubmit(async (values) => {
    const payload = { ...values, materia_id: contexto.materiaId || values.materia_id };
    if (editing_id) {
      await actualizar_mutation.mutateAsync({ id: editing_id, data: payload });
    } else {
      await crear_mutation.mutateAsync(payload);
    }
    form.reset();
    set_show_form(false);
    set_editing_id(null);
  });

  const handle_eliminar = async () => {
    if (!delete_id) return;
    await eliminar_mutation.mutateAsync(delete_id);
    set_delete_id(null);
  };

  const handle_export_lms = async () => {
    if (!contexto.materiaId || !contexto.cohorteId) return;
    set_export_loading(true);
    try {
      const blob = await exportarLMS(contexto.materiaId, contexto.cohorteId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "fechas-lms-export.csv";
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      set_export_loading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Fechas Académicas</h1>
          <p className="mt-1 text-sm text-gray-500">Cronograma de evaluaciones y fechas importantes</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={handle_export_lms} is_loading={export_loading} disabled={!contexto.materiaId || !contexto.cohorteId}>
            Exportar LMS
          </Button>
          <Button onClick={() => { set_show_form(!show_form); set_editing_id(null); form.reset(); }}>
            {show_form ? "Cancelar" : "Nueva fecha"}
          </Button>
        </div>
      </div>

      <ContextoAcademicoSelector onChange={set_contexto} />

      {show_form && (
        <form onSubmit={handle_submit} className="rounded-lg border bg-white p-4 shadow-sm space-y-4">
          <div className="grid gap-4 sm:grid-cols-4">
            <FormField label="Título" html_for="titulo" error={form.formState.errors.titulo?.message}>
              <Input id="titulo" {...form.register("titulo", { required: true })} has_error={!!form.formState.errors.titulo} />
            </FormField>
            <FormField label="Tipo" html_for="tipo">
              <select id="tipo" {...form.register("tipo")} className="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500">
                {tipos.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </FormField>
            <FormField label="Fecha" html_for="fecha_evaluacion" error={form.formState.errors.fecha_evaluacion?.message}>
              <Input id="fecha_evaluacion" type="datetime-local" {...form.register("fecha_evaluacion", { required: true })} has_error={!!form.formState.errors.fecha_evaluacion} />
            </FormField>
            <FormField label="N° instancia" html_for="numero_instancia">
              <Input id="numero_instancia" type="number" min={1} {...form.register("numero_instancia", { valueAsNumber: true })} />
            </FormField>
          </div>
          <div className="flex justify-end gap-3">
            <Button type="submit" is_loading={crear_mutation.isPending || actualizar_mutation.isPending}>
              {editing_id ? "Actualizar" : "Crear"}
            </Button>
          </div>
        </form>
      )}

      <FilterableTable
        columns={columns}
        data={items}
        total={items.length}
        isLoading={isLoading}
        error={error?.message ?? null}
        exportFileName="fechas-academicas.csv"
      />

      <ConfirmDialog
        isOpen={!!delete_id}
        onConfirm={handle_eliminar}
        onCancel={() => set_delete_id(null)}
        title="Eliminar fecha"
        message="¿Estás seguro de eliminar esta fecha académica?"
        variant="danger"
        confirmLabel="Eliminar"
      />
    </div>
  );
}
