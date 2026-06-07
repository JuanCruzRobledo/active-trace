import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import type { Mock } from "vitest";

const mockUpdateMutate = vi.fn();

vi.mock("@/features/comision/hooks/useUmbralMateria", () => ({
  useUmbralMateria: vi.fn(),
  useUpdateUmbral: vi.fn(),
}));

import {
  useUmbralMateria,
  useUpdateUmbral,
} from "@/features/comision/hooks/useUmbralMateria";
import { UmbralPage } from "@/features/comision/pages/UmbralPage";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/comision/mat-001/umbral"]}>
        <Routes>
          <Route path="comision/:materiaId/umbral" element={<UmbralPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  (useUmbralMateria as unknown as Mock).mockReturnValue({
    data: { materia_id: "mat-001", porcentaje: 60 },
    isLoading: false,
    isError: false,
    error: null,
  });
  (useUpdateUmbral as unknown as Mock).mockReturnValue({
    mutate: mockUpdateMutate,
    isPending: false,
    isError: false,
    error: null,
  });
});

afterEach(cleanup);

describe("UmbralPage", () => {
  it("shows the current umbral value", () => {
    renderPage();
    expect(screen.getByText("Umbral de aprobación")).toBeInTheDocument();
    const input = screen.getByRole("spinbutton");
    expect(input).toHaveValue(60);
  });

  it("calls update mutation on save", async () => {
    const user = userEvent.setup();
    renderPage();
    const input = screen.getByRole("spinbutton");
    await user.clear(input);
    await user.type(input, "70");
    await user.click(screen.getByText("Guardar"));
    expect(mockUpdateMutate).toHaveBeenCalledWith(70, expect.any(Object));
  });

  it("shows validation error for out of range value", async () => {
    const user = userEvent.setup();
    renderPage();
    const input = screen.getByRole("spinbutton");
    await user.clear(input);
    await user.type(input, "150");
    await user.click(screen.getByText("Guardar"));
    expect(
      screen.getByText("El porcentaje debe estar entre 0 y 100."),
    ).toBeInTheDocument();
    expect(mockUpdateMutate).not.toHaveBeenCalled();
  });

  it("shows success message after update", async () => {
    const user = userEvent.setup();
    (useUpdateUmbral as unknown as Mock).mockReturnValue({
      mutate: (_val: number, opts?: { onSuccess?: () => void }) => {
        opts?.onSuccess?.();
      },
      isPending: false,
      isError: false,
      error: null,
    });
    renderPage();
    await user.click(screen.getByText("Guardar"));
    expect(
      screen.getByText("Umbral actualizado correctamente."),
    ).toBeInTheDocument();
  });

  it("shows error state when loading fails", () => {
    (useUmbralMateria as unknown as Mock).mockReturnValue({
      data: null,
      isLoading: false,
      isError: true,
      error: new Error("Error de conexión"),
    });
    renderPage();
    expect(screen.getByText("Error de conexión")).toBeInTheDocument();
  });
});
