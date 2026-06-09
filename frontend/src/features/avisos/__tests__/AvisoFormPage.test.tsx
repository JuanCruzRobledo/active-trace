import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import type { Mock } from "vitest";

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );
  return {
    ...actual,
    useParams: vi.fn(),
  };
});

vi.mock("@/features/avisos/hooks/useAvisos", () => ({
  useAvisoById: vi.fn(),
  useCrearAviso: vi.fn(),
  useActualizarAviso: vi.fn(),
}));

import { useParams } from "react-router-dom";
import {
  useAvisoById,
  useCrearAviso,
  useActualizarAviso,
} from "@/features/avisos/hooks/useAvisos";
import { AvisoFormPage } from "@/features/avisos/pages/AvisoFormPage";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <AvisoFormPage />
      </BrowserRouter>
    </QueryClientProvider>,
  );
}

const mockAviso = {
  id: "b1a2c3d4-e5f6-7890-abcd-ef1234567890",
  alcance: "global",
  severidad: "warning",
  titulo: "Aviso importante",
  cuerpo: "Contenido del aviso",
  inicio_en: "2026-06-01",
  fin_en: "2026-06-30",
  orden: 1,
  requiere_ack: false,
  activo: true,
  materia_id: null,
  cohorte_id: null,
  rol_destino: null,
  created_at: "2026-06-01T00:00:00Z",
  updated_at: null,
  total_ack: 0,
  total_usuarios_alcance: 10,
  porcentaje_ack: 0,
};

beforeEach(() => {
  vi.clearAllMocks();
  (useParams as unknown as Mock).mockReturnValue({ id: undefined });
  (useCrearAviso as unknown as Mock).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  });
  (useActualizarAviso as unknown as Mock).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  });
  (useAvisoById as unknown as Mock).mockReturnValue({
    data: null,
    isLoading: false,
    isError: false,
    error: null,
  });
});

afterEach(cleanup);

describe("AvisoFormPage", () => {
  it("renders in create mode", () => {
    renderPage();
    expect(screen.getByText("Nuevo Aviso")).toBeInTheDocument();
    expect(
      screen.getByText("Creá un nuevo aviso para comunicar a los docentes"),
    ).toBeInTheDocument();
    expect(screen.getByText("Crear aviso")).toBeInTheDocument();
  });

  it("renders in edit mode with aviso data", () => {
    (useParams as unknown as Mock).mockReturnValue({
      id: "b1a2c3d4-e5f6-7890-abcd-ef1234567890",
    });
    (useAvisoById as unknown as Mock).mockReturnValue({
      data: mockAviso,
      isLoading: false,
      isError: false,
      error: null,
    });

    renderPage();
    expect(screen.getByText("Editar Aviso")).toBeInTheDocument();
    expect(
      screen.getByText("Actualizá los datos del aviso"),
    ).toBeInTheDocument();
    expect(screen.getByText("Guardar cambios")).toBeInTheDocument();
  });

  it("shows loading state in edit mode while fetching", () => {
    (useParams as unknown as Mock).mockReturnValue({
      id: "b1a2c3d4-e5f6-7890-abcd-ef1234567890",
    });
    (useAvisoById as unknown as Mock).mockReturnValue({
      data: null,
      isLoading: true,
      isError: false,
      error: null,
    });

    renderPage();
    // Loading spinner replaces the form — no title rendered
    expect(screen.queryByText("Nuevo Aviso")).not.toBeInTheDocument();
    expect(screen.queryByText("Guardar cambios")).not.toBeInTheDocument();
  });

  it("shows validation errors when submitting empty form", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByText("Crear aviso"));

    await waitFor(() => {
      const alerts = screen.getAllByRole("alert");
      expect(alerts.length).toBeGreaterThan(0);
    });
  });

  it("renders all required form fields", () => {
    renderPage();
    expect(screen.getByLabelText("Alcance")).toBeInTheDocument();
    expect(screen.getByLabelText("Severidad")).toBeInTheDocument();
    expect(screen.getByLabelText("Título")).toBeInTheDocument();
    expect(screen.getByLabelText("Cuerpo")).toBeInTheDocument();
    expect(screen.getByLabelText("Inicio")).toBeInTheDocument();
    expect(screen.getByLabelText("Fin")).toBeInTheDocument();
    expect(screen.getByLabelText("Orden")).toBeInTheDocument();
  });

  it("calls crearAviso on valid submit", async () => {
    const mockCrear = vi.fn().mockResolvedValue(undefined);
    (useCrearAviso as unknown as Mock).mockReturnValue({
      mutateAsync: mockCrear,
      isPending: false,
    });
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByLabelText("Título"), "Test title");
    await user.type(screen.getByLabelText("Cuerpo"), "Test body");
    await user.type(screen.getByLabelText("Inicio"), "2026-06-01");
    await user.type(screen.getByLabelText("Fin"), "2026-06-30");
    await user.type(screen.getByLabelText("Orden"), "1");

    await user.click(screen.getByText("Crear aviso"));

    await waitFor(() => {
      expect(mockCrear).toHaveBeenCalled();
    });
  });
});
