import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import type { Mock } from "vitest";

vi.mock("@/features/monitores/hooks/useMonitorSeguimiento", () => ({
  useMonitorSeguimiento: vi.fn(),
}));

vi.mock("@/features/monitores/hooks/useMonitorGeneral", () => ({
  useMonitorGeneral: vi.fn(),
}));

vi.mock("@/features/monitores/services/seguimiento", () => ({
  exportarMonitores: vi.fn(),
}));

import { useMonitorSeguimiento } from "@/features/monitores/hooks/useMonitorSeguimiento";
import { useMonitorGeneral } from "@/features/monitores/hooks/useMonitorGeneral";
import { MonitoresPage } from "@/features/monitores/pages/MonitoresPage";
import { exportarMonitores } from "@/features/monitores/services/seguimiento";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/monitores"]}>
        <Routes>
          <Route path="monitores" element={<MonitoresPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const mockSeguimientoData = {
  items: [
    {
      alumno_id: "a1",
      alumno: "Ana Gomez",
      correo: "ana@test.com",
      comision: "A-101",
      materia: "Matemática",
      actividad: "TP1",
      estado: "aprobada",
      nota: 8,
    },
    {
      alumno_id: "a2",
      alumno: "Luis Paz",
      correo: "luis@test.com",
      comision: "B-202",
      materia: "Física",
      actividad: "TP2",
      estado: "pendiente",
      nota: null,
    },
  ],
  total: 2,
};

const mockGeneralData = {
  items: [
    {
      alumno_id: "g1",
      alumno: "Carlos Ruiz",
      correo: "carlos@test.com",
      comision: "C-303",
      materia: "Química",
      total_actividades: 10,
      aprobadas: 7,
      pendientes: 3,
      ultima_actividad: "TP4",
      estado_general: "en_seguimiento" as const,
    },
  ],
  total: 1,
};

beforeEach(() => {
  vi.clearAllMocks();
  (useMonitorSeguimiento as unknown as Mock).mockReturnValue({
    data: mockSeguimientoData,
    isLoading: false,
    isError: false,
    error: null,
  });
  (useMonitorGeneral as unknown as Mock).mockReturnValue({
    data: mockGeneralData,
    isLoading: false,
    isError: false,
    error: null,
  });
  vi.mocked(exportarMonitores).mockResolvedValue(
    new Blob(["csv"], { type: "text/csv" }),
  );
});

afterEach(cleanup);

describe("MonitoresPage", () => {
  it("renders seguimiento tab by default with monitor data", () => {
    renderPage();
    expect(screen.getByText("Monitor de seguimiento")).toBeInTheDocument();
    expect(screen.getByText("Ana Gomez")).toBeInTheDocument();
    expect(screen.getByText("Luis Paz")).toBeInTheDocument();
    expect(screen.getByText("ana@test.com")).toBeInTheDocument();
  });

  it("shows all filter inputs in seguimiento tab", () => {
    renderPage();
    expect(screen.getByPlaceholderText("Filtrar por nombre")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Filtrar por correo")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Comisión")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Materia")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Actividad")).toBeInTheDocument();
  });

  it("shows date range filter inputs in seguimiento tab", () => {
    renderPage();
    // Buscamos los inputs de tipo date por su label
    expect(screen.getByText("Desde")).toBeInTheDocument();
    expect(screen.getByText("Hasta")).toBeInTheDocument();
  });

  it("calls export on button click", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByText("Exportar"));
    expect(exportarMonitores).toHaveBeenCalled();
  });

  it("shows clear filters button and clears filters", async () => {
    const user = userEvent.setup();
    renderPage();
    const nombreInput = screen.getByPlaceholderText("Filtrar por nombre");
    await user.type(nombreInput, "Ana");
    expect(screen.getByText("Limpiar filtros")).toBeInTheDocument();
    await user.click(screen.getByText("Limpiar filtros"));
    expect(nombreInput).toHaveValue("");
  });

  it("shows empty state when no seguimiento data", () => {
    (useMonitorSeguimiento as unknown as Mock).mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      isError: false,
      error: null,
    });
    renderPage();
    expect(
      screen.getByText("No tienes alumnos asignados actualmente"),
    ).toBeInTheDocument();
  });

  it("shows error state in seguimiento", () => {
    (useMonitorSeguimiento as unknown as Mock).mockReturnValue({
      data: null,
      isLoading: false,
      isError: true,
      error: new Error("Error del servidor"),
    });
    renderPage();
    expect(screen.getByText("Error del servidor")).toBeInTheDocument();
  });

  it("shows loading state without crashing", () => {
    (useMonitorSeguimiento as unknown as Mock).mockReturnValue({
      data: null,
      isLoading: true,
      isError: false,
      error: null,
    });
    renderPage();
    expect(screen.getByText("Monitor de seguimiento")).toBeInTheDocument();
    expect(screen.queryByText("Ana Gomez")).not.toBeInTheDocument();
  });

  it("switches to general tab and shows general content", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByText("General"));
    await waitFor(() => {
      expect(screen.getByText("Monitor General")).toBeInTheDocument();
    });
    expect(
      screen.getByText("Estado general de actividades por alumno"),
    ).toBeInTheDocument();
  });

  it("shows general table data when general tab is active", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByText("General"));
    await waitFor(() => {
      expect(screen.getByText("Carlos Ruiz")).toBeInTheDocument();
    });
    expect(screen.getByText("carlos@test.com")).toBeInTheDocument();
  });

  it("shows general view filter inputs", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByText("General"));
    await waitFor(() => {
      expect(screen.getByText("Monitor General")).toBeInTheDocument();
    });
    expect(screen.getByPlaceholderText("Regional")).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText("Comisión"),
    ).toBeInTheDocument();
  });

  it("switches back to seguimiento tab after viewing general", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByText("General"));
    await waitFor(() => {
      expect(screen.getByText("Monitor General")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Seguimiento"));
    expect(screen.getByText("Monitor de seguimiento")).toBeInTheDocument();
    expect(screen.getByText("Ana Gomez")).toBeInTheDocument();
  });
});
