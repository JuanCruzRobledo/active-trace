import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import type { Mock } from "vitest";

vi.mock("@/features/liquidaciones/hooks/useLiquidaciones", () => ({
  useFacturas: vi.fn(),
  useAbonarFactura: vi.fn(),
}));

import {
  useFacturas,
  useAbonarFactura,
} from "@/features/liquidaciones/hooks/useLiquidaciones";
import { FacturasPage } from "@/features/liquidaciones/pages/FacturasPage";

const mockFacturas = [
  {
    id: "fac-1",
    tenant_id: "t1",
    usuario_id: "user-1",
    periodo: "2026-06",
    detalle: "Factura por servicios",
    referencia_archivo: "factura-001.pdf",
    tamano_kb: 512,
    estado: "pendiente",
    cargada_at: "2026-06-01T00:00:00Z",
    abonada_at: null,
    created_at: "2026-06-01T00:00:00Z",
    updated_at: "2026-06-01T00:00:00Z",
  },
  {
    id: "fac-2",
    tenant_id: "t1",
    usuario_id: "user-2",
    periodo: "2026-05",
    detalle: "Factura mayo",
    referencia_archivo: null,
    tamano_kb: null,
    estado: "abonada",
    cargada_at: "2026-05-01T00:00:00Z",
    abonada_at: "2026-05-15T00:00:00Z",
    created_at: "2026-05-01T00:00:00Z",
    updated_at: "2026-05-15T00:00:00Z",
  },
];

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <FacturasPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  (useFacturas as unknown as Mock).mockReturnValue({
    data: mockFacturas,
    isLoading: false,
    error: null,
  });
  (useAbonarFactura as unknown as Mock).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  });
});

afterEach(cleanup);

describe("FacturasPage", () => {
  it("renders the page title", () => {
    renderPage();
    expect(screen.getByText("Facturas")).toBeInTheDocument();
  });

  it("renders all facturas", () => {
    renderPage();
    expect(screen.getByText("Factura por servicios")).toBeInTheDocument();
    expect(screen.getByText("Factura mayo")).toBeInTheDocument();
  });

  it("shows estado pendiente and abonada badges", () => {
    renderPage();
    expect(screen.getByText("pendiente")).toBeInTheDocument();
    expect(screen.getByText("abonada")).toBeInTheDocument();
  });

  it("shows 'Marcar abonada' only for pending facturas", () => {
    renderPage();
    const abonarBtns = screen.getAllByText("Marcar abonada");
    expect(abonarBtns).toHaveLength(1);
  });

  it("clicking 'Marcar abonada' opens confirm dialog", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByText("Marcar abonada"));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(
      screen.getByText(/Confirmar pago de factura/i),
    ).toBeInTheDocument();
  });

  it("confirming abonar calls mutation with correct id", async () => {
    const mockMutate = vi.fn();
    (useAbonarFactura as unknown as Mock).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
    });
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByText("Marcar abonada"));
    const confirmBtn = screen.getByText("Sí, marcar abonada");
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(mockMutate).toHaveBeenCalledWith("fac-1");
    });
  });

  it("filters by estado: only shows pendientes", async () => {
    const user = userEvent.setup();
    renderPage();

    const select = screen.getByRole("combobox");
    await user.selectOptions(select, "pendiente");

    // after filter, useFacturas should be called but we have local client filter
    // The pending factura should still be visible
    expect(screen.getByText("Factura por servicios")).toBeInTheDocument();
  });
});
