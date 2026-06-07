import { STEPS } from "@/features/setup-cuatrimestre/types/setup-cuatrimestre";
import type { WizardStep, CompletedSteps } from "@/features/setup-cuatrimestre/hooks/useSetupCuatrimestre";

export function StepIndicator({
  current,
  completed,
}: {
  current: WizardStep;
  completed: CompletedSteps;
}) {
  return (
    <nav aria-label="Progress" className="mb-8">
      <ol className="flex items-center gap-1 overflow-x-auto">
        {STEPS.map((s, i) => {
          const is_done = completed[s.key as keyof CompletedSteps];
          const is_current = current === s.key;
          return (
            <li key={s.key} className="flex items-center gap-1 text-xs whitespace-nowrap">
              {i > 0 && <span className="text-gray-300 mx-1">→</span>}
              <span
                className={`flex items-center gap-1 rounded-full px-2.5 py-1 font-medium ${
                  is_done
                    ? "bg-green-100 text-green-700"
                    : is_current
                      ? "bg-brand-100 text-brand-700"
                      : "bg-gray-100 text-gray-400"
                }`}
              >
                {is_done ? (
                  <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                    <path
                      fillRule="evenodd"
                      d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
                      clipRule="evenodd"
                    />
                  </svg>
                ) : (
                  <span>{s.key}</span>
                )}
                {s.label}
              </span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
