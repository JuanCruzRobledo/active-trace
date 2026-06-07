import { useState } from "react";
import { Button } from "@/shared/components/Button";
import { useSetupCuatrimestre } from "@/features/setup-cuatrimestre/hooks/useSetupCuatrimestre";
import { StepIndicator } from "@/features/setup-cuatrimestre/components/StepIndicator";
import { StepCrearCohorte } from "@/features/setup-cuatrimestre/components/StepCrearCohorte";
import { StepClonarEquipo } from "@/features/setup-cuatrimestre/components/StepClonarEquipo";
import { StepAjustarAsignaciones } from "@/features/setup-cuatrimestre/components/StepAjustarAsignaciones";
import { StepCargarProgramas } from "@/features/setup-cuatrimestre/components/StepCargarProgramas";
import { StepCargarFechas } from "@/features/setup-cuatrimestre/components/StepCargarFechas";
import { StepPublicarAviso } from "@/features/setup-cuatrimestre/components/StepPublicarAviso";
import { StepResumen } from "@/features/setup-cuatrimestre/components/StepResumen";

export function SetupCuatrimestreWizard() {
  const { state, mark_completed, reset } = useSetupCuatrimestre();
  const [show_finish, set_show_finish] = useState(false);

  if (show_finish) {
    return (
      <div className="space-y-6">
        <div className="rounded-lg border border-green-200 bg-green-50 p-8 text-center">
          <svg
            className="mx-auto h-12 w-12 text-green-500"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z"
              clipRule="evenodd"
            />
          </svg>
          <h2 className="mt-4 text-xl font-semibold text-green-800">Setup completado</h2>
          <p className="mt-2 text-sm text-green-600">El cuatrimestre fue configurado correctamente.</p>
          <Button className="mt-4" onClick={reset}>
            Configurar otro cuatrimestre
          </Button>
        </div>
      </div>
    );
  }

  const render_step = () => {
    switch (state.step) {
      case 1:
        return <StepCrearCohorte on_complete={(id) => mark_completed(1, id)} />;
      case 2:
        return (
          <StepClonarEquipo
            cohorte_id={state.cohorte_id!}
            on_complete={() => mark_completed(2)}
            on_skip={() => mark_completed(2)}
          />
        );
      case 3:
        return (
          <StepAjustarAsignaciones
            on_complete={() => mark_completed(3)}
            on_skip={() => mark_completed(3)}
          />
        );
      case 4:
        return (
          <StepCargarProgramas
            cohorte_id={state.cohorte_id!}
            on_complete={() => mark_completed(4)}
            on_skip={() => mark_completed(4)}
          />
        );
      case 5:
        return (
          <StepCargarFechas
            cohorte_id={state.cohorte_id!}
            on_complete={() => mark_completed(5)}
            on_skip={() => mark_completed(5)}
          />
        );
      case 6:
        return (
          <StepPublicarAviso
            cohorte_id={state.cohorte_id!}
            on_complete={() => mark_completed(6)}
            on_skip={() => mark_completed(6)}
          />
        );
      case 7:
        return <StepResumen completed={state.completed} on_finish={() => set_show_finish(true)} />;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Setup de cuatrimestre</h1>
        <p className="mt-1 text-sm text-gray-500">Configuración guiada para un nuevo cuatrimestre</p>
      </div>

      <StepIndicator current={state.step} completed={state.completed} />

      {render_step()}
    </div>
  );
}
