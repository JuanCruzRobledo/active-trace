import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import type { Mock } from "vitest";

vi.mock("@/features/tareas/hooks/useTareas", () => ({
  useTareaById: vi.fn(),
  useAgregarComentario: vi.fn(),
  useActualizarEstadoTarea: vi.fn(),
}));

import {
  useTareaById,
  useAgregarComentario,
  useActualizarEstadoTarea,
} from "@/features/tareas/hooks/useTareas";
import { TareaDetailPanel } from "@/features/tareas/components/TareaDetailPanel";

function renderPanel(tareaId: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <TareaDetailPanel tareaId={tareaId} onClose={vi.fn()} />
    </QueryClientProvider>,
  );
}

const mockTarea = {
  id: "t1",
  tenant_id: "tenant-1",
  materia_id: null,
  asignado_a: "user-1",
  asignado_por: "admin-1",
  estado: "pendiente",
  descripcion: "Completar informe mensual",
  contexto_id: null,
  created_at: "2026-06-01T10:00:00Z",
  updated_at: "2026-06-01T10:00:00Z",
  comentarios: [
    {
      id: "c1",
      tarea_id: "t1",
      autor_id: "user-1",
      texto: "Estoy trabajando en esto",
      creado_at: "2026-06-01T12:00:00Z",
    },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
  (useTareaById as unknown as Mock).mockReturnValue({
    data: mockTarea,
    isLoading: false,
    isError: false,
    error: null,
  });
  (useAgregarComentario as unknown as Mock).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  });
  (useActualizarEstadoTarea as unknown as Mock).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  });
});

afterEach(cleanup);

describe("TareaDetailPanel", () => {
  it("renders task details", () => {
    renderPanel("t1");
    expect(screen.getByText("Detalle de Tarea")).toBeInTheDocument();
    expect(
      screen.getByText("Completar informe mensual"),
    ).toBeInTheDocument();
  });

  it("shows task id", () => {
    renderPanel("t1");
    expect(screen.getByText("t1")).toBeInTheDocument();
  });

  it("shows loading state", () => {
    (useTareaById as unknown as Mock).mockReturnValue({
      data: null,
      isLoading: true,
      isError: false,
      error: null,
    });
    renderPanel("t1");
    // should not crash, loading spinner shown
    expect(screen.queryByText("Detalle de Tarea")).not.toBeInTheDocument();
  });

  it("shows error state", () => {
    (useTareaById as unknown as Mock).mockReturnValue({
      data: null,
      isLoading: false,
      isError: true,
      error: new Error("Error al cargar"),
    });
    renderPanel("t1");
    expect(screen.getByText("Error al cargar")).toBeInTheDocument();
  });

  it("renders timeline status buttons", () => {
    renderPanel("t1");
    expect(screen.getByText("pendiente")).toBeInTheDocument();
    expect(screen.getByText("en curso")).toBeInTheDocument();
    expect(screen.getByText("completada")).toBeInTheDocument();
    expect(screen.getByText("cancelada")).toBeInTheDocument();
  });

  it("renders existing comment", () => {
    renderPanel("t1");
    expect(screen.getByText("Estoy trabajando en esto")).toBeInTheDocument();
  });

  it("shows comment count", () => {
    renderPanel("t1");
    expect(screen.getByText("Comentarios (1)")).toBeInTheDocument();
  });

  it("calls actualizarEstado when clicking a timeline button", async () => {
    const mockActualizar = vi.fn();
    (useActualizarEstadoTarea as unknown as Mock).mockReturnValue({
      mutate: mockActualizar,
      isPending: false,
    });
    const user = userEvent.setup();
    renderPanel("t1");

    const enCursoBtn = screen.getByText("en curso");
    await user.click(enCursoBtn);

    await waitFor(() => {
      expect(mockActualizar).toHaveBeenCalledWith({
        id: "t1",
        payload: { nuevo_estado: "en_curso" },
      });
    });
  });

  it("calls agregarComentario when sending a comment", async () => {
    const mockAgregar = vi.fn().mockResolvedValue(undefined);
    (useAgregarComentario as unknown as Mock).mockReturnValue({
      mutateAsync: mockAgregar,
      isPending: false,
    });
    const user = userEvent.setup();
    renderPanel("t1");

    const input = screen.getByPlaceholderText("Escribí un comentario...");
    await user.type(input, "Nuevo comentario");

    await user.click(screen.getByText("Enviar"));

    await waitFor(() => {
      expect(mockAgregar).toHaveBeenCalledWith({
        tareaId: "t1",
        payload: { texto: "Nuevo comentario" },
      });
    });
  });

  it("calls onClose when close button is clicked", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <TareaDetailPanel tareaId="t1" onClose={onClose} />
      </QueryClientProvider>,
    );

    const buttons = screen.getAllByRole("button");
    // The close button is the first button (before timeline buttons)
    const closeBtn = buttons[0]!;
    await user.click(closeBtn);
    expect(onClose).toHaveBeenCalled();
  });
});
