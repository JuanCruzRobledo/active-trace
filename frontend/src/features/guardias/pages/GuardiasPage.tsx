import { useState } from "react";
import { useForm } from "react-hook-form";
import { FilterableTable, type Column } from "@/shared/components/FilterableTable";
import { Button } from "@/shared/components/Button";
import { Input } from "@/shared/components/Input";
import { FormField } from "@/shared/components/FormField";
import { ConfirmDialog } from "@/shared/components/ConfirmDialog";
import { useGuardias, useCrearGuardia, useActualizarGuardia } from "@/features/guardias/hooks/useGuardias";
import type { Guardia, GuardiaCreate, GuardiaFilters } from "@/features/guardias/types/guardias";

const estados = ["pendiente", "activa", "finalizada", "cancelada"];

const columns: Column<Guardia>[] = [
  { key: "fecha", label: "Fecha", sortable: true },
  { key: "hora_inicio", label: "Inicio", sortable: true },
  { key: "hora_fin", label: "Fin", sortable: true },
  {
    key: "estado",
    label: "Estado",
    sortable: true,
    render: (row) => (
      <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
        row.estado === "activa" ? "bg-green-100 text-green-800"
        : row.estado === "pendiente" ? "bg-yellow-100 text-yellow-800"
        : row.estado === "finalizada" ? "bg-blue-100 text-blue-800"
        : "bg-gray-100 text-gray-800"
      }`}>
        {row.estado}
      </span>
    ),
  },
  { key: "comentarios", label: "Comentarios" },
];

export function GuardiasPage() {
  const [filters, set_filters] = useState<GuardiaFilters>({});
  const [show_form, set_show_form] = useState(false);
  const [editing_id, set_editing_id] = useState<string | null>(null);
  const [cancel_id, set_cancel_id] = useState<string | null>(null);

  const { data, isLoading, error } = useGuardias(filters);
  const crear_mutation = useCrearGuardia();
  const actualizar_mutation = useActualizarGuardia();

  const form = useForm<GuardiaCreate>({
    defaultValues: { fecha: "", hora_inicio: "", hora_fin: "", estado: "pendiente", comentarios: "" },
  });

  const items = data?.items ?? [];

  const handle_submit = form.handleSubmit(async (values) => {
    if (editing_id) {
      await actualizar_mutation.mutateAsync({ id: editing_id, data: values });
    } else {
      await crear_mutation.mutateAsync(values);
    }
    form.reset();
    set_show_form(false);
    set_editing_id(null);
  });

  const handle_cancel = async () => {
    if (!cancel_id) return;
    await actualizar_mutation.mutateAsync({ id: cancel_id, data: { estado: "cancelada" } });
    set_cancel_id(null);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Guardias</h1>
          <p className="mt-1 text-sm text-gray-500">Registro y seguimiento de guardias docentes</p>
        </div>
        <Button onClick={() => { set_show_form(!show_form); set_editing_id(null); form.reset(); }}>
          {show_form ? "Cancelar" : "Nueva guardia"}
        </Button>
      </div>

      {show_form && (
        <form onSubmit={handle_submit} className="rounded-lg border bg-white p-4 shadow-sm space-y-4">
          <div className="grid gap-4 sm:grid-cols-5">
            <FormField label="Fecha" html_for="fecha" error={form.formState.errors.fecha?.message}>
              <Input id="fecha" type="date" {...form.register("fecha", { required: true })} has_error={!!form.formState.errors.fecha} />
            </FormField>
            <FormField label="Inicio" html_for="hora_inicio" error={form.formState.errors.hora_inicio?.message}>
              <Input id="hora_inicio" type="time" {...form.register("hora_inicio", { required: true })} has_error={!!form.formState.errors.hora_inicio} />
            </FormField>
            <FormField label="Fin" html_for="hora_fin" error={form.formState.errors.hora_fin?.message}>
              <Input id="hora_fin" type="time" {...form.register("hora_fin", { required: true })} has_error={!!form.formState.errors.hora_fin} />
            </FormField>
            <FormField label="Estado" html_for="estado">
              <select id="estado" {...form.register("estado")} className="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500">
                {estados.map((e) => <option key={e} value={e}>{e}</option>)}
              </select>
            </FormField>
            <FormField label="Comentarios" html_for="comentarios">
              <Input id="comentarios" {...form.register("comentarios")} />
            </FormField>
          </div>
          <div className="flex justify-end gap-3">
            <Button type="submit" is_loading={crear_mutation.isPending || actualizar_mutation.isPending}>
              {editing_id ? "Actualizar" : "Crear"}
            </Button>
          </div>
        </form>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 rounded-lg border bg-white p-4 shadow-sm">
        <div className="w-40">
          <label className="mb-1 block text-xs font-medium text-gray-600">Desde</label>
          <Input type="date" value={filters.desde ?? ""} onChange={(e) => set_filters((p) => ({ ...p, desde: e.target.value || undefined }))} />
        </div>
        <div className="w-40">
          <label className="mb-1 block text-xs font-medium text-gray-600">Hasta</label>
          <Input type="date" value={filters.hasta ?? ""} onChange={(e) => set_filters((p) => ({ ...p, hasta: e.target.value || undefined }))} />
        </div>
        <div className="w-36">
          <label className="mb-1 block text-xs font-medium text-gray-600">Estado</label>
          <select value={filters.estado ?? ""} onChange={(e) => set_filters((p) => ({ ...p, estado: e.target.value || undefined }))}
            className="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500">
            <option value="">Todos</option>
            {estados.map((e) => <option key={e} value={e}>{e}</option>)}
          </select>
        </div>
      </div>

      <FilterableTable
        columns={columns}
        data={items}
        total={items.length}
        isLoading={isLoading}
        error={error?.message ?? null}
        exportFileName="guardias.csv"
      />

      <ConfirmDialog
        isOpen={!!cancel_id}
        onConfirm={handle_cancel}
        onCancel={() => set_cancel_id(null)}
        title="Cancelar guardia"
        message="¿Estás seguro de cancelar esta guardia?"
        variant="warning"
        confirmLabel="Cancelar guardia"
      />
    </div>
  );
}
