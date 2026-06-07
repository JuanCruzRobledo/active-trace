import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import type { Mock } from "vitest";

const mockComunicacionesRefetch = vi.fn();
const mockDestinatariosRefetch = vi.fn();

vi.mock("@/features/comision/hooks/useComunicaciones", () => ({
  useComunicaciones: vi.fn(),
  useAlumnosAtrasadosParaComunicacion: vi.fn(),
  useCrearComunicacion: vi.fn(),
  useComunicacionPolling: vi.fn(),
}));

import {
  useComunicaciones,
  useAlumnosAtrasadosParaComunicacion,
  useCrearComunicacion,
  useComunicacionPolling,
} from "@/features/comision/hooks/useComunicaciones";
import { ComunicacionesPage } from "@/features/comision/pages/ComunicacionesPage";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/comision/mat-001/comunicaciones"]}>
        <Routes>
          <Route
            path="comision/:materiaId/comunicaciones"
            element={<ComunicacionesPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const mockComunicaciones = {
  items: [
    {
      id: "c1",
      asunto: "Aviso de atraso",
      estado: "Enviado" as const,
      total_destinatarios: 5,
      enviados: 5,
      fallidos: 0,
      created_at: "2025-03-01T12:00:00Z",
      materia_id: "mat-001",
    },
  ],
  total: 1,
};

const mockDestinatarios = [
  { alumno_id: "a1", alumno: "Pedro Diaz", legajo: "3001", seleccionado: true },
  { alumno_id: "a2", alumno: "Sofia Torres", legajo: "3002", seleccionado: true },
];

const mockCrearMutate = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  mockComunicacionesRefetch.mockReset();
  mockDestinatariosRefetch.mockReset();
  (useComunicaciones as unknown as Mock).mockReturnValue({
    data: mockComunicaciones,
    isLoading: false,
    isError: false,
    error: null,
    refetch: mockComunicacionesRefetch,
  });
  (useAlumnosAtrasadosParaComunicacion as unknown as Mock).mockReturnValue({
    data: mockDestinatarios,
    isLoading: false,
    isError: false,
    error: null,
    refetch: mockDestinatariosRefetch,
  });
  mockCrearMutate.mockImplementation(
    (_req: any, opts?: { onSuccess?: (result: { id: string }) => void }) => {
      opts?.onSuccess?.({ id: "new-c1" });
    },
  );
  (useCrearComunicacion as unknown as Mock).mockReturnValue({
    mutate: mockCrearMutate,
    isPending: false,
    isError: false,
    error: null,
  });
  (useComunicacionPolling as unknown as Mock).mockReturnValue({
    data: null,
    isLoading: false,
  });
});

afterEach(cleanup);

describe("ComunicacionesPage", () => {
  it("shows historial de comunicaciones", () => {
    renderPage();
    expect(screen.getByText("Comunicaciones")).toBeInTheDocument();
    expect(screen.getByText("Aviso de atraso")).toBeInTheDocument();
    expect(screen.getByText("Enviado")).toBeInTheDocument();
  });

  it("shows nueva comunicacion button", () => {
    renderPage();
    expect(screen.getByText("Nueva comunicación")).toBeInTheDocument();
  });

  it("opens editor when clicking nueva comunicacion", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByText("Nueva comunicación"));
    expect(screen.getByPlaceholderText("Asunto del mensaje")).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText("Escribí el mensaje..."),
    ).toBeInTheDocument();
  });

  it("shows preview step after filling editor and clicking previsualizar", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByText("Nueva comunicación"));
    await user.type(screen.getByPlaceholderText("Asunto del mensaje"), "Test asunto");
    await user.type(
      screen.getByPlaceholderText("Escribí el mensaje..."),
      "Test cuerpo",
    );
    const checkboxes = screen.getAllByRole("checkbox");
    for (const cb of checkboxes) {
      await user.click(cb);
    }
    await user.click(screen.getByText("Previsualizar"));
    expect(screen.getByText("Vista previa del mensaje")).toBeInTheDocument();
    expect(screen.getByText("Test asunto")).toBeInTheDocument();
    expect(screen.getByText("Test cuerpo")).toBeInTheDocument();
  });

  it("sends communication from preview", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByText("Nueva comunicación"));
    await user.type(screen.getByPlaceholderText("Asunto del mensaje"), "Test");
    await user.type(screen.getByPlaceholderText("Escribí el mensaje..."), "Body");
    const checkboxes = screen.getAllByRole("checkbox");
    for (const cb of checkboxes) {
      await user.click(cb);
    }
    await user.click(screen.getByText("Previsualizar"));
    await user.click(screen.getByText("Enviar"));
    expect(mockCrearMutate).toHaveBeenCalled();
  });

  it("shows tracking progress when polling active", async () => {
    const user = userEvent.setup();
    (useComunicacionPolling as unknown as Mock).mockReturnValue({
      data: {
        id: "new-c1",
        asunto: "Test",
        estado: "En envío" as const,
        total_destinatarios: 5,
        enviados: 3,
        fallidos: 0,
        created_at: "2025-03-01T12:00:00Z",
        materia_id: "mat-001",
      },
      isLoading: false,
    });
    renderPage();
    await user.click(screen.getByText("Nueva comunicación"));
    await user.type(screen.getByPlaceholderText("Asunto del mensaje"), "Test");
    await user.type(screen.getByPlaceholderText("Escribí el mensaje..."), "Body");
    const checkboxes = screen.getAllByRole("checkbox");
    for (const cb of checkboxes) {
      await user.click(cb);
    }
    await user.click(screen.getByText("Previsualizar"));
    await user.click(screen.getByText("Enviar"));
    expect(screen.getByText(/3 de 5 enviados/)).toBeInTheDocument();
    expect(screen.getByText("En envío")).toBeInTheDocument();
  });

  it("shows tracking failed state", async () => {
    const user = userEvent.setup();
    (useComunicacionPolling as unknown as Mock).mockReturnValue({
      data: {
        id: "new-c1",
        asunto: "Test",
        estado: "Fallido" as const,
        total_destinatarios: 5,
        enviados: 2,
        fallidos: 3,
        created_at: "2025-03-01T12:00:00Z",
        materia_id: "mat-001",
      },
      isLoading: false,
    });
    renderPage();
    await user.click(screen.getByText("Nueva comunicación"));
    await user.type(screen.getByPlaceholderText("Asunto del mensaje"), "Test");
    await user.type(screen.getByPlaceholderText("Escribí el mensaje..."), "Body");
    const checkboxes = screen.getAllByRole("checkbox");
    for (const cb of checkboxes) {
      await user.click(cb);
    }
    await user.click(screen.getByText("Previsualizar"));
    await user.click(screen.getByText("Enviar"));
    expect(
      screen.getByText(/La comunicación no pudo completarse/),
    ).toBeInTheDocument();
  });

  it("shows empty history when no comunicaciones", () => {
    (useComunicaciones as unknown as Mock).mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      isError: false,
      error: null,
      refetch: mockComunicacionesRefetch,
    });
    renderPage();
    expect(
      screen.getByText("No hay comunicaciones enviadas aún."),
    ).toBeInTheDocument();
  });
});
