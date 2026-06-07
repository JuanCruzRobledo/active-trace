import { useState, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/services/api";
import { Button } from "@/shared/components/Button";
import { subirPrograma } from "@/features/programas/services/programas";
import type { CarreraOption } from "@/features/setup-cuatrimestre/types/setup-cuatrimestre";

export function StepCargarProgramas({
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
  const file_ref = useRef<HTMLInputElement>(null);

  const materias_query = useQuery({
    queryKey: ["materias", cohorte_id],
    queryFn: () => api.get<CarreraOption[]>(`/cohortes/${cohorte_id}/materias`).then((r) => r.data),
    enabled: !!cohorte_id,
  });

  const handle_subir = async () => {
    const file = file_ref.current?.files?.[0];
    if (!file || !materia_id) return;
    set_loading(true);
    try {
      const form = new FormData();
      form.append("archivo", file);
      form.append("materia_id", materia_id);
      form.append("cohorte_id", cohorte_id);
      await subirPrograma(form);
      on_complete();
    } finally {
      set_loading(false);
    }
  };

  return (
    <div className="space-y-4 rounded-lg border bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900">Cargar programas</h2>
      <p className="text-sm text-gray-500">Subí los programas de estudio para las materias de este cuatrimestre.</p>
      <div className="flex items-end gap-3">
        <div className="flex-1">
          <label className="mb-1 block text-sm font-medium text-gray-700">Materia</label>
          <select
            value={materia_id}
            onChange={(e) => set_materia_id(e.target.value)}
            className="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">Seleccionar materia</option>
            {(materias_query.data ?? []).map((m) => (
              <option key={m.id} value={m.id}>
                {m.nombre}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <input
          ref={file_ref}
          type="file"
          accept=".pdf,.doc,.docx"
          className="block w-full text-sm file:mr-4 file:rounded-md file:border-0 file:bg-brand-50 file:px-4 file:py-2 file:text-sm file:font-medium file:text-brand-700 hover:file:bg-brand-100"
        />
        <Button onClick={handle_subir} is_loading={loading} disabled={!materia_id}>
          Subir
        </Button>
      </div>
      <div className="flex justify-end">
        <Button variant="ghost" onClick={on_skip}>
          Saltar este paso
        </Button>
      </div>
    </div>
  );
}
