import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import type { Mock } from "vitest";

vi.mock("@/features/comision/hooks/useReportes", () => ({
  useReportes: vi.fn(),
}));

vi.mock("@/features/comision/services/reportes", () => ({
  exportarEntregasSinCorregir: vi.fn(),
}));

import { useReportes } from "@/features/comision/hooks/useReportes";
import { ReportesPage } from "@/features/comision/pages/ReportesPage";
import { exportarEntregasSinCorregir } from "@/features/comision/services/reportes";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/comision/mat-001/reportes"]}>
        <Routes>
          <Route path="comision/:materiaId/reportes" element={<ReportesPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const mockReportes = {
  total_alumnos: 30,
  actividades_registradas: 5,
  porcentaje_aprobacion: 75,
  alumnos_atrasados: 8,
  alumnos_al_dia: 22,
  tiene_datos: true,
};

beforeEach(() => {
  vi.clearAllMocks();
  (useReportes as unknown as Mock).mockReturnValue({
    data: mockReportes,
    isLoading: false,
    isError: false,
    error: null,
  });
  vi.mocked(exportarEntregasSinCorregir).mockResolvedValue(
    new Blob(["csv content"], { type: "text/csv" }),
  );
});

afterEach(cleanup);

describe("ReportesPage", () => {
  it("renders metric cards with data", () => {
    renderPage();
    expect(screen.getByText("Reportes")).toBeInTheDocument();
    expect(screen.getByText("30")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("75")).toBeInTheDocument();
    expect(screen.getByText("8")).toBeInTheDocument();
    expect(screen.getByText("22")).toBeInTheDocument();
  });

  it("renders export button", () => {
    renderPage();
    expect(
      screen.getByText("Exportar entregas sin corregir"),
    ).toBeInTheDocument();
  });

  it("shows empty state when no data", () => {
    (useReportes as unknown as Mock).mockReturnValue({
      data: {
        total_alumnos: 0,
        actividades_registradas: 0,
        porcentaje_aprobacion: 0,
        alumnos_atrasados: 0,
        alumnos_al_dia: 0,
        tiene_datos: false,
      },
      isLoading: false,
      isError: false,
      error: null,
    });
    renderPage();
    expect(screen.getByText("No hay datos disponibles")).toBeInTheDocument();
    expect(
      screen.getByText(/Importe calificaciones primero/),
    ).toBeInTheDocument();
  });

  it("shows error state", () => {
    (useReportes as unknown as Mock).mockReturnValue({
      data: null,
      isLoading: false,
      isError: true,
      error: new Error("Error al cargar reportes"),
    });
    renderPage();
    expect(screen.getByText("Error al cargar reportes")).toBeInTheDocument();
  });
});
