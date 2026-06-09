import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import type { Mock } from "vitest";

vi.mock("@/features/equipos/hooks/useEquipos", () => ({
  useAsignacionMasiva: vi.fn(),
}));

import { useAsignacionMasiva } from "@/features/equipos/hooks/useEquipos";
import { AsignacionMasivaPage } from "@/features/equipos/pages/AsignacionMasivaPage";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <AsignacionMasivaPage />
      </BrowserRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  (useAsignacionMasiva as unknown as Mock).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
    isSuccess: false,
  });
});

afterEach(cleanup);

describe("AsignacionMasivaPage", () => {
  it("renders the form with title and description", () => {
    renderPage();
    expect(screen.getByText("Asignación Masiva")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Asigná múltiples docentes a una materia, carrera y cohorte",
      ),
    ).toBeInTheDocument();
  });

  it("renders role select and date inputs", () => {
    renderPage();
    expect(screen.getByLabelText("Rol")).toBeInTheDocument();
    expect(screen.getByLabelText("Desde")).toBeInTheDocument();
    expect(screen.getByLabelText("Hasta (opcional)")).toBeInTheDocument();
  });

  it("renders usuario_ids textarea", () => {
    renderPage();
    expect(
      screen.getByText("IDs de usuarios (uno por línea)"),
    ).toBeInTheDocument();
  });

  it("shows submit and cancel buttons", () => {
    renderPage();
    expect(screen.getByText("Asignar")).toBeInTheDocument();
    expect(screen.getByText("Cancelar")).toBeInTheDocument();
  });

  it("renders contexto academico selector with select inputs", () => {
    renderPage();
    expect(screen.getByText("Carrera")).toBeInTheDocument();
    expect(screen.getByText("Cohorte")).toBeInTheDocument();
    expect(screen.getByText("Materia")).toBeInTheDocument();
  });

  it("shows success message after submission", () => {
    (useAsignacionMasiva as unknown as Mock).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      isSuccess: true,
    });

    renderPage();
    expect(
      screen.getByText("Asignación masiva completada exitosamente"),
    ).toBeInTheDocument();
  });
});
