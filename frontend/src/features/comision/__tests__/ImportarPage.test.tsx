import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import type { Mock } from "vitest";

const mockPreviewMutate = vi.fn();
const mockImportMutate = vi.fn();
const mockReset = vi.fn();

vi.mock("@/features/comision/hooks/useImportarCalificaciones", () => ({
  usePreviewCalificaciones: vi.fn(),
  useImportarCalificaciones: vi.fn(),
}));

import {
  usePreviewCalificaciones,
  useImportarCalificaciones,
} from "@/features/comision/hooks/useImportarCalificaciones";
import { ImportarPage } from "@/features/comision/pages/ImportarPage";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/comision/mat-001/importar"]}>
        <Routes>
          <Route path="comision/:materiaId/importar" element={<ImportarPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  (usePreviewCalificaciones as unknown as Mock).mockReturnValue({
    mutate: mockPreviewMutate,
    isPending: false,
    isError: false,
    error: null,
    data: null,
    reset: mockReset,
  });
  (useImportarCalificaciones as unknown as Mock).mockReturnValue({
    mutate: mockImportMutate,
    isPending: false,
    isError: false,
    error: null,
  });
});

afterEach(cleanup);

describe("ImportarPage", () => {
  it("renders the upload form", () => {
    renderPage();
    expect(screen.getByText("Importar Calificaciones")).toBeInTheDocument();
    expect(screen.getByLabelText("Archivo de calificaciones")).toBeInTheDocument();
    expect(screen.getByText("Previsualizar")).toBeInTheDocument();
  });

  it("shows preview table after successful preview", () => {
    (usePreviewCalificaciones as unknown as Mock).mockReturnValue({
      mutate: mockPreviewMutate,
      isPending: false,
      isError: false,
      error: null,
      data: {
        filas: [
          { alumno: "Juan Perez", legajo: "12345", actividad: "TP1", nota: 8 },
          { alumno: "Ana Lopez", legajo: "12346", actividad: "TP1", nota: 9 },
        ],
        actividades: ["TP1"],
        total_filas: 2,
      },
      reset: mockReset,
    });
    renderPage();
    expect(screen.getByText("Juan Perez")).toBeInTheDocument();
    expect(screen.getByText("Ana Lopez")).toBeInTheDocument();
    expect(screen.getByText("Confirmar importación")).toBeInTheDocument();
    expect(screen.getByText("Cancelar")).toBeInTheDocument();
  });

  it("shows success summary after confirming import", async () => {
    const user = userEvent.setup();
    const successFn = vi.fn();
    (usePreviewCalificaciones as unknown as Mock).mockReturnValue({
      mutate: mockPreviewMutate,
      isPending: false,
      isError: false,
      error: null,
      data: {
        filas: [
          { alumno: "Juan Perez", legajo: "12345", actividad: "TP1", nota: 8 },
        ],
        actividades: ["TP1"],
        total_filas: 1,
      },
      reset: mockReset,
    });
    (useImportarCalificaciones as unknown as Mock).mockReturnValue({
      mutate: (_acts: string[], opts?: { onSuccess?: (r: { importadas: number; errores: number }) => void }) => {
        opts?.onSuccess?.({ importadas: 10, errores: 0 });
        successFn();
      },
      isPending: false,
      isError: false,
      error: null,
    });
    renderPage();
    await user.click(screen.getByText("Confirmar importación"));
    expect(successFn).toHaveBeenCalled();
  });

  it("shows error message when preview fails", () => {
    (usePreviewCalificaciones as unknown as Mock).mockReturnValue({
      mutate: mockPreviewMutate,
      isPending: false,
      isError: true,
      error: new Error("Formato inválido"),
      data: null,
      reset: mockReset,
    });
    renderPage();
    expect(screen.getByText("Formato inválido")).toBeInTheDocument();
    expect(screen.getByText("Reintentar")).toBeInTheDocument();
  });
});
