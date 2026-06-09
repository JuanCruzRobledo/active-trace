import { useState, useCallback } from "react";

export type WizardStep = 1 | 2 | 3 | 4 | 5 | 6 | 7;

export interface CompletedSteps {
  1: boolean;
  2: boolean;
  3: boolean;
  4: boolean;
  5: boolean;
  6: boolean;
  7: boolean;
}

export interface WizardState {
  step: WizardStep;
  cohorte_id: string | null;
  completed: CompletedSteps;
}

const initial_state: WizardState = {
  step: 1,
  cohorte_id: null,
  completed: { 1: false, 2: false, 3: false, 4: false, 5: false, 6: false, 7: false },
};

export function useSetupCuatrimestre() {
  const [state, set_state] = useState<WizardState>(initial_state);

  const set_step = useCallback((step: WizardStep) => {
    set_state((prev) => ({ ...prev, step }));
  }, []);

  const mark_completed = useCallback((step: WizardStep, cohorte_id?: string) => {
    set_state((prev) => ({
      ...prev,
      cohorte_id: cohorte_id ?? prev.cohorte_id,
      completed: { ...prev.completed, [step]: true },
      step: Math.min(7, (step + 1) as WizardStep) as WizardStep,
    }));
  }, []);

  const reset = useCallback(() => {
    set_state(initial_state);
  }, []);

  return { state, set_step, mark_completed, reset };
}
