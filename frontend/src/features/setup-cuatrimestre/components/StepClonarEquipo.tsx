import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/services/api";
import { Button } from "@/shared/components/Button";
import { clonarEquipo } from "@/features/setup-cuatrimestre/services/setup-cuatrimestre";
import type { CarreraOption } from "@/features/setup-cuatrimestre/types/setup-cuatrimestre";

export function StepClonarEquipo({
  cohorte_id,
  on_complete,
  on_skip,
}: {
  cohorte_id: string;
  on_complete: () => void;
  on_skip: () => void;
}) {
  const [loading, set_loading] = useState(false);
  const [origen_id, set_origen_id] = useState("");

  const cohortes_query = useQuery({
    queryKey: ["cohortes"],
    queryFn: () => api.get<CarreraOption[]>("/cohortes").then((r) => r.data),
  });

  const handle_clonar = async () => {
    if (!origen_id) return;
    set_loading(true);
    try {
      await clonarEquipo(origen_id, cohorte_id);
      on_complete();
    } finally {
      set_loading(false);
    }
  };

  return (
    <div className="space-y-4 rounded-lg border bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900">Clonar equipo docente</h2>
      <p className="text-sm text-gray-500">Copiá la configuración de equipo de un cuatrimestre anterior.</p>
      <div className="flex items-end gap-3">
        <div className="flex-1">
          <label className="mb-1 block text-sm font-medium text-gray-700">Cohorte origen</label>
          <select
            value={origen_id}
            onChange={(e) => set_origen_id(e.target.value)}
            className="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">Seleccionar cohorte</option>
            {(cohortes_query.data ?? [])
              .filter((c) => c.id !== cohorte_id)
              .map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre}
                </option>
              ))}
          </select>
        </div>
        <Button onClick={handle_clonar} is_loading={loading} disabled={!origen_id}>
          Clonar
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
