import { useState, useRef } from "react";
import { FilterableTable, type Column } from "@/shared/components/FilterableTable";
import { ContextoAcademicoSelector } from "@/shared/components/ContextoAcademicoSelector";
import { Button } from "@/shared/components/Button";
import { ConfirmDialog } from "@/shared/components/ConfirmDialog";
import { useProgramas, useSubirPrograma, useEliminarPrograma } from "@/features/programas/hooks/useProgramas";
import type { Programa } from "@/features/programas/types/programas";

const columns: Column<Programa>[] = [
  { key: "nombre", label: "Nombre", sortable: true },
  { key: "tipo", label: "Tipo", sortable: true },
  { key: "subido_en", label: "Subido", sortable: true },
  {
    key: "archivo_url",
    label: "Archivo",
    render: (row) => (
      <a href={row.archivo_url} target="_blank" rel="noopener noreferrer" className="text-brand-600 hover:text-brand-800 underline">
        Descargar
      </a>
    ),
  },
];

export function ProgramasPage() {
  const [contexto, set_contexto] = useState({ carreraId: "", cohorteId: "", materiaId: "" });
  const [show_form, set_show_form] = useState(false);
  const [delete_id, set_delete_id] = useState<string | null>(null);
  const file_ref = useRef<HTMLInputElement>(null);

  const filters = contexto.materiaId ? { materia_id: contexto.materiaId, carrera_id: contexto.carreraId, cohorte_id: contexto.cohorteId } : undefined;
  const { data, isLoading, error } = useProgramas(filters);
  const subir_mutation = useSubirPrograma();
  const eliminar_mutation = useEliminarPrograma();

  const items = data?.items ?? [];

  const handle_subir = async () => {
    const file = file_ref.current?.files?.[0];
    if (!file || !contexto.materiaId) return;
    const form = new FormData();
    form.append("archivo", file);
    form.append("materia_id", contexto.materiaId);
    if (contexto.carreraId) form.append("carrera_id", contexto.carreraId);
    if (contexto.cohorteId) form.append("cohorte_id", contexto.cohorteId);
    await subir_mutation.mutateAsync(form);
    if (file_ref.current) file_ref.current.value = "";
    set_show_form(false);
  };

  const handle_eliminar = async () => {
    if (!delete_id) return;
    await eliminar_mutation.mutateAsync(delete_id);
    set_delete_id(null);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Programas</h1>
          <p className="mt-1 text-sm text-gray-500">Gestión de programas de estudio por materia</p>
        </div>
        <Button onClick={() => set_show_form(!show_form)} disabled={!contexto.materiaId}>
          {show_form ? "Cancelar" : "Subir programa"}
        </Button>
      </div>

      <ContextoAcademicoSelector onChange={set_contexto} />

      {show_form && (
        <div className="rounded-lg border bg-white p-4 shadow-sm space-y-4">
          <div className="flex items-center gap-4">
            <input
              ref={file_ref}
              type="file"
              accept=".pdf,.doc,.docx,.txt"
              className="block w-full text-sm text-gray-500 file:mr-4 file:rounded-md file:border-0 file:bg-brand-50 file:px-4 file:py-2 file:text-sm file:font-medium file:text-brand-700 hover:file:bg-brand-100"
            />
            <Button onClick={handle_subir} is_loading={subir_mutation.isPending} disabled={!contexto.materiaId}>
              Subir
            </Button>
          </div>
          {!contexto.materiaId && <p className="text-xs text-amber-600">Seleccioná una materia primero</p>}
        </div>
      )}

      <FilterableTable
        columns={columns}
        data={items}
        total={items.length}
        isLoading={isLoading}
        error={error?.message ?? null}
        exportFileName="programas.csv"
      />

      <ConfirmDialog
        isOpen={!!delete_id}
        onConfirm={handle_eliminar}
        onCancel={() => set_delete_id(null)}
        title="Eliminar programa"
        message="¿Estás seguro de eliminar este programa? Esta acción no se puede deshacer."
        variant="danger"
        confirmLabel="Eliminar"
      />
    </div>
  );
}
