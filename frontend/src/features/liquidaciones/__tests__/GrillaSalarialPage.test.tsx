import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import type { Mock } from "vitest";

vi.mock("@/features/liquidaciones/hooks/useLiquidaciones", () => ({
  useSalariosBase: vi.fn(),
  useSalariosPlus: vi.fn(),
  useClavesPlusByActive: vi.fn(),
  useCrearSalarioBase: vi.fn(),
  useCrearSalarioPlus: vi.fn(),
  useCrearClavePlus: vi.fn(),
}));

import {
  useSalariosBase,
  useSalariosPlus,
  useClavesPlusByActive,
  useCrearSalarioBase,
  useCrearSalarioPlus,
  useCrearClavePlus,
} from "@/features/liquidaciones/hooks/useLiquidaciones";
import { GrillaSalarialPage } from "@/features/liquidaciones/pages/GrillaSalarialPage";

const mockSalariosBase = [
  {
    id: "sb-1",
    tenant_id: "t1",
    rol: "TUTOR",
    monto: "10000.00",
    desde: "2026-01-01",
    hasta: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
];

const mockSalariosPlus = [
  {
    id: "sp-1",
    tenant_id: "t1",
    grupo: "ANTIGUEDAD",
    rol: "TUTOR",
    descripcion: "Plus por antigüedad",
    monto: "500.00",
    desde: "2026-01-01",
    hasta: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
];

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <GrillaSalarialPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  (useSalariosBase as unknown as Mock).mockReturnValue({
    data: mockSalariosBase,
    isLoading: false,
    error: null,
  });
  (useSalariosPlus as unknown as Mock).mockReturnValue({
    data: mockSalariosPlus,
    isLoading: false,
    error: null,
  });
  (useClavesPlusByActive as unknown as Mock).mockReturnValue({
    data: [],
    isLoading: false,
    error: null,
  });
  (useCrearSalarioBase as unknown as Mock).mockReturnValue({
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
  });
  (useCrearSalarioPlus as unknown as Mock).mockReturnValue({
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
  });
  (useCrearClavePlus as unknown as Mock).mockReturnValue({
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
  });
});

afterEach(cleanup);

describe("GrillaSalarialPage", () => {
  it("renders the page title", () => {
    renderPage();
    expect(screen.getByText("Grilla Salarial")).toBeInTheDocument();
  });

  it("renders salarios base section", () => {
    renderPage();
    expect(screen.getByText("Salarios Base")).toBeInTheDocument();
    // TUTOR appears in both salarios base and salarios plus tables
    const tutorCells = screen.getAllByText("TUTOR");
    expect(tutorCells.length).toBeGreaterThan(0);
  });

  it("renders salarios plus section", () => {
    renderPage();
    expect(screen.getByText("Salarios Plus")).toBeInTheDocument();
    expect(screen.getByText("ANTIGUEDAD")).toBeInTheDocument();
  });

  it("shows add salario base form when clicking the button", async () => {
    const user = userEvent.setup();
    renderPage();
    const addBtn = screen.getAllByText("Agregar")[0]!;
    await user.click(addBtn);
    expect(screen.getByLabelText(/Rol/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Monto/i)).toBeInTheDocument();
  });

  it("validates salario base form: empty rol shows error", async () => {
    const user = userEvent.setup();
    renderPage();
    const addBtn = screen.getAllByText("Agregar")[0]!;
    await user.click(addBtn);

    const submitBtn = screen.getByText("Guardar salario base");
    await user.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("El rol es obligatorio")).toBeInTheDocument();
    });
  });

  it("submits salario base form with valid data", async () => {
    const mockMutate = vi.fn().mockResolvedValue({});
    (useCrearSalarioBase as unknown as Mock).mockReturnValue({
      mutateAsync: mockMutate,
      isPending: false,
    });
    const user = userEvent.setup();
    renderPage();

    const addBtn = screen.getAllByText("Agregar")[0]!;
    await user.click(addBtn);

    await user.type(screen.getByLabelText(/Rol/i), "TUTOR");
    await user.type(screen.getByLabelText(/Monto/i), "10000");

    await user.click(screen.getByText("Guardar salario base"));

    await waitFor(() => {
      expect(mockMutate).toHaveBeenCalledWith(
        expect.objectContaining({ rol: "TUTOR", monto: "10000" }),
      );
    });
  });
});
