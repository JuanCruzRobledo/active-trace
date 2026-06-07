import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi, describe, it, expect, beforeEach } from "vitest";
import type { Mock } from "vitest";

vi.mock("@/features/comision/hooks/useAtrasados", () => ({
  useAtrasados: vi.fn(),
}));

import { useAtrasados } from "@/features/comision/hooks/useAtrasados";
import { AtrasadosPage } from "@/features/comision/pages/AtrasadosPage";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/comision/mat-001/atrasados"]}>
        <Routes>
          <Route path="comision/:materiaId/atrasados" element={<AtrasadosPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const mockData = {
  items: [
    {
      alumno_id: "a1",
      alumno: "Carlos Gomez",
      legajo: "1001",
      actividades_faltantes: 3,
      total_actividades: 5,
      nota_actual: 4,
      estado: "atrasado" as const,
      riesgo: "alto" as const,
    },
    {
      alumno_id: "a2",
      alumno: "Maria Ruiz",
      legajo: "1002",
      actividades_faltantes: 1,
      total_actividades: 5,
      nota_actual: 7,
      estado: "al_dia" as const,
      riesgo: "bajo" as const,
    },
  ],
  total: 2,
};

beforeEach(() => {
  vi.clearAllMocks();
  (useAtrasados as unknown as Mock).mockReturnValue({
    data: mockData,
    isLoading: false,
    isError: false,
    error: null,
  });
});

describe("AtrasadosPage", () => {
  it("renders the table with atrasados data", () => {
    renderPage();
    expect(screen.getByText("Alumnos atrasados")).toBeInTheDocument();
    expect(screen.getByText("Carlos Gomez")).toBeInTheDocument();
    expect(screen.getByText("Maria Ruiz")).toBeInTheDocument();
    expect(screen.getByText("1001")).toBeInTheDocument();
    expect(screen.getByText("1002")).toBeInTheDocument();
  });

  it("shows filter inputs", () => {
    renderPage();
    expect(screen.getByPlaceholderText("Filtrar por nombre")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Actividad")).toBeInTheDocument();
  });

  it("shows empty state when no atrasados", () => {
    (useAtrasados as unknown as Mock).mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      isError: false,
      error: null,
    });
    renderPage();
    expect(
      screen.getByText("No hay alumnos atrasados en esta materia"),
    ).toBeInTheDocument();
  });

  it("shows loading spinner", () => {
    (useAtrasados as unknown as Mock).mockReturnValue({
      data: null,
      isLoading: true,
      isError: false,
      error: null,
    });
    renderPage();
    expect(screen.getByText("Alumnos atrasados")).toBeInTheDocument();
  });

  it("shows error state", () => {
    (useAtrasados as unknown as Mock).mockReturnValue({
      data: null,
      isLoading: false,
      isError: true,
      error: new Error("Error al cargar"),
    });
    renderPage();
    expect(screen.getByText("Error al cargar")).toBeInTheDocument();
  });
});
