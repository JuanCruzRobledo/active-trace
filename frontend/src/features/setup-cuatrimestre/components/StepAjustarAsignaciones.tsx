import { Button } from "@/shared/components/Button";

export function StepAjustarAsignaciones({
  on_complete: _on_complete,
  on_skip,
}: {
  on_complete: () => void;
  on_skip: () => void;
}) {
  return (
    <div className="space-y-4 rounded-lg border bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900">Ajustar asignaciones</h2>
      <p className="text-sm text-gray-500">Revisá y ajustá las asignaciones de los docentes a las materias.</p>
      <div className="flex gap-3">
        <a
          href="/equipos/asignaciones"
          className="inline-flex items-center gap-2 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          Ir a asignaciones
        </a>
        <Button variant="ghost" onClick={on_skip}>
          Saltar este paso
        </Button>
      </div>
    </div>
  );
}
