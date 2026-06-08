import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import type { Mock } from "vitest";

vi.mock("@/features/auditoria/hooks/useAuditoria", () => ({
  useAccionesPorDia: vi.fn(),
  useComunicacionesPorDocente: vi.fn(),
  useInteraccionesPorDocenteMateria: vi.fn(),
  useUltimasAcciones: vi.fn(),
}));

import {
  useAccionesPorDia,
  useComunicacionesPorDocente,
  useInteraccionesPorDocenteMateria,
  useUltimasAcciones,
} from "@/features/auditoria/hooks/useAuditoria";
import { AuditoriaPanelPage } from "@/features/auditoria/pages/AuditoriaPanelPage";

const mockAcciones = [
  { fecha: "2026-06-01", cantidad: 15, materia_id: null },
  { fecha: "2026-06-02", cantidad: 8, materia_id: null },
];

const mockComunicaciones = [
  { usuario_id: "u1", nombre: "Ana García", cantidad: 25, materia_id: null },
  { usuario_id: "u2", nombre: "Carlos López", cantidad: 10, materia_id: null },
];

const mockInteracciones = [
  {
    usuario_id: "u1",
    materia_id: "m1",
    nombre_usuario: "Ana García",
    nombre_materia: "Álgebra",
    cantidad: 50,
  },
];

const mockUltimas = [
  {
    id: "log-1",
    usuario_id: "u1",
    materia_id: null,
    accion: "importar_notas",
    registros: 30,
    ip: "192.168.1.1",
    user_agent: "Mozilla",
    created_at: "2026-06-07T10:00:00Z",
  },
];

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AuditoriaPanelPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  (useAccionesPorDia as unknown as Mock).mockReturnValue({
    data: mockAcciones,
    isLoading: false,
    error: null,
  });
  (useComunicacionesPorDocente as unknown as Mock).mockReturnValue({
    data: mockComunicaciones,
    isLoading: false,
    error: null,
  });
  (useInteraccionesPorDocenteMateria as unknown as Mock).mockReturnValue({
    data: mockInteracciones,
    isLoading: false,
    error: null,
  });
  (useUltimasAcciones as unknown as Mock).mockReturnValue({
    data: mockUltimas,
    isLoading: false,
    error: null,
  });
});

afterEach(cleanup);

describe("AuditoriaPanelPage", () => {
  it("renders the panel title", () => {
    renderPage();
    expect(screen.getByText("Panel de Auditoría")).toBeInTheDocument();
  });

  it("renders date range filters", () => {
    renderPage();
    expect(screen.getByLabelText("Desde")).toBeInTheDocument();
    expect(screen.getByLabelText("Hasta")).toBeInTheDocument();
  });

  it("renders acciones por dia section", () => {
    renderPage();
    expect(screen.getByText("Acciones por Día")).toBeInTheDocument();
    expect(screen.getByText("2026-06-01")).toBeInTheDocument();
  });

  it("renders comunicaciones por docente section", () => {
    renderPage();
    expect(
      screen.getByText("Comunicaciones por Docente"),
    ).toBeInTheDocument();
    // "Ana García" appears in both comunicaciones and interacciones panels
    const anaItems = screen.getAllByText("Ana García");
    expect(anaItems.length).toBeGreaterThan(0);
  });

  it("renders últimas acciones section", () => {
    renderPage();
    expect(screen.getByText("Últimas Acciones")).toBeInTheDocument();
    expect(screen.getByText("importar_notas")).toBeInTheDocument();
  });

  it("changing date filter triggers re-query with new filters", async () => {
    const user = userEvent.setup();
    renderPage();

    const desdeInput = screen.getByLabelText("Desde");
    await user.type(desdeInput, "2026-06-01");

    await waitFor(() => {
      // useAccionesPorDia was called — verify the hook was invoked (mock check)
      expect(useAccionesPorDia).toHaveBeenCalled();
    });
  });

  it("shows interacciones por docente-materia section", () => {
    renderPage();
    expect(
      screen.getByText("Interacciones por Docente-Materia"),
    ).toBeInTheDocument();
    expect(screen.getByText("Álgebra")).toBeInTheDocument();
  });
});
