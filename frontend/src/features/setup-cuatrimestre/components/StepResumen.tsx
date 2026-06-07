import { STEPS } from "@/features/setup-cuatrimestre/types/setup-cuatrimestre";
import { Button } from "@/shared/components/Button";
import type { CompletedSteps } from "@/features/setup-cuatrimestre/hooks/useSetupCuatrimestre";

export function StepResumen({
  completed,
  on_finish,
}: {
  completed: CompletedSteps;
  on_finish: () => void;
}) {
  const all_done = Object.values(completed).every(Boolean);
  const count = Object.values(completed).filter(Boolean).length;

  return (
    <div className="space-y-4 rounded-lg border bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900">Resumen del setup</h2>
      <p className="text-sm text-gray-500">
        {all_done
          ? "Todos los pasos completados. ¡Cuatrimestre listo!"
          : `${count} de 7 pasos completados. Podés completar los restantes desde los módulos correspondientes.`}
      </p>
      <div className="space-y-2">
        {STEPS.map((s) => {
          const done = completed[s.key as keyof CompletedSteps];
          return (
            <div key={s.key} className="flex items-center gap-2 text-sm">
              {done ? (
                <svg className="h-5 w-5 text-green-500" viewBox="0 0 20 20" fill="currentColor">
                  <path
                    fillRule="evenodd"
                    d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
                    clipRule="evenodd"
                  />
                </svg>
              ) : (
                <span className="flex h-5 w-5 items-center justify-center rounded-full border border-gray-300 text-xs text-gray-400">
                  —
                </span>
              )}
              <span className={done ? "text-gray-900 font-medium" : "text-gray-400"}>{s.label}</span>
            </div>
          );
        })}
      </div>
      <div className="flex justify-end pt-4">
        <Button onClick={on_finish}>Finalizar</Button>
      </div>
    </div>
  );
}
