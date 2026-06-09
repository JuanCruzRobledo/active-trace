import { render, screen, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import type { Mock } from "vitest";

vi.mock("@/features/liquidaciones/hooks/useLiquidaciones", () => ({
  useLiquidaciones: vi.fn(),
  useCerrarLiquidacion: vi.fn(),
}));

import {
  useLiquidaciones,
  useCerrarLiquidacion,
} from "@/features/liquidaciones/hooks/useLiquidaciones";
import { LiquidacionPeriodoPage } from "@/features/liquidaciones/pages/LiquidacionPeriodoPage";

const mockLiquidaciones = [
  // General segment
  {
    id: "liq-1",
    tenant_id: "t1",
    cohorte_id: "c1",
    periodo: "2026-06",
    usuario_id: "user-general-1",
    rol: "TUTOR",
    comisiones: 2,
    monto_base: "10000.00",
    monto_plus: "500.00",
    total: "10500.00",
    es_nexo: false,
    excluido_por_factura: false,
    estado: "abierta",
    cerrada_at: null,
    created_at: "2026-06-01T00:00:00Z",
    updated_at: "2026-06-01T00:00:00Z",
  },
  // NEXO segment
  {
    id: "liq-2",
    tenant_id: "t1",
    cohorte_id: "c1",
    periodo: "2026-06",
    usuario_id: "user-nexo-1",
    rol: "NEXO",
    comisiones: 3,
    monto_base: "15000.00",
    monto_plus: "750.00",
    total: "15750.00",
    es_nexo: true,
    excluido_por_factura: false,
    estado: "abierta",
    cerrada_at: null,
    created_at: "2026-06-01T00:00:00Z",
    updated_at: "2026-06-01T00:00:00Z",
  },
  // Facturan segment (informational, NOT summed)
  {
    id: "liq-3",
    tenant_id: "t1",
    cohorte_id: "c1",
    periodo: "2026-06",
    usuario_id: "user-factura-1",
    rol: "TUTOR",
    comisiones: 1,
    monto_base: "5000.00",
    monto_plus: "0.00",
    total: "5000.00",
    es_nexo: false,
    excluido_por_factura: true,
    estado: "abierta",
    cerrada_at: null,
    created_at: "2026-06-01T00:00:00Z",
    updated_at: "2026-06-01T00:00:00Z",
  },
];

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <LiquidacionPeriodoPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  (useLiquidaciones as unknown as Mock).mockReturnValue({
    data: mockLiquidaciones,
    isLoading: false,
    error: null,
  });
  (useCerrarLiquidacion as unknown as Mock).mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  });
});

afterEach(cleanup);

describe("LiquidacionPeriodoPage", () => {
  it("renders the page title", () => {
    renderPage();
    expect(screen.getByText("Liquidaciones del Período")).toBeInTheDocument();
  });

  it("renders the three segments", () => {
    renderPage();
    expect(screen.getByText("Segmento General")).toBeInTheDocument();
    expect(screen.getByText("Segmento NEXO")).toBeInTheDocument();
    // "Docentes Facturadores" appears in both the section h2 and the KPI label
    const facturItems = screen.getAllByText(/Docentes Facturadores/i);
    expect(facturItems.length).toBeGreaterThan(0);
  });

  it("renders KPI header with total sin factura", () => {
    renderPage();
    expect(screen.getByTestId("kpi-total-sin-factura")).toBeInTheDocument();
  });

  it("facturadores segment is labeled as informational only", () => {
    renderPage();
    expect(screen.getByText("Solo informativo")).toBeInTheDocument();
  });

  it("RN-35: docentes that facturan are NOT summed into total sin factura", () => {
    renderPage();
    const totalSinFactura = screen.getByTestId("kpi-total-sin-factura");
    // total sin factura = general (10500) + nexo (15750) = 26250
    // facturan (5000) should NOT be included
    expect(totalSinFactura.textContent).toContain("26.250");
  });

  it("RN-35: facturan total is shown separately as informational", () => {
    renderPage();
    const totalFacturan = screen.getByTestId("kpi-total-facturan");
    expect(totalFacturan.textContent).toContain("5.000");
    // And the informational label is present
    expect(
      screen.getByText("Informativo — no sumado al total"),
    ).toBeInTheDocument();
  });

  it("shows loading state", () => {
    (useLiquidaciones as unknown as Mock).mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
    });
    renderPage();
    expect(screen.queryByText("Segmento General")).not.toBeInTheDocument();
  });

  it("renders close button for open liquidaciones", () => {
    renderPage();
    const cerrarButtons = screen.getAllByText("Cerrar");
    expect(cerrarButtons.length).toBeGreaterThan(0);
  });
});
