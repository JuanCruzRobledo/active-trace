import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import type { Mock } from "vitest";

vi.mock("@/features/comision/hooks/useRanking", () => ({
  useRanking: vi.fn(),
  useNotasFinales: vi.fn(),
}));

import {
  useRanking,
  useNotasFinales,
} from "@/features/comision/hooks/useRanking";
import { RankingsPage } from "@/features/comision/pages/RankingsPage";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/comision/mat-001/rankings"]}>
        <Routes>
          <Route path="comision/:materiaId/rankings" element={<RankingsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const mockRankingData = {
  items: [
    {
      alumno_id: "a1",
      alumno: "Luis Martinez",
      legajo: "2001",
      actividades_aprobadas: 8,
      total_actividades: 10,
      porcentaje: 80,
    },
  ],
  total: 1,
};

const mockNotasData = {
  items: [
    {
      alumno_id: "a1",
      alumno: "Luis Martinez",
      legajo: "2001",
      nota_final: 8.5,
    },
  ],
  total: 1,
};

beforeEach(() => {
  vi.clearAllMocks();
  (useRanking as unknown as Mock).mockReturnValue({
    data: mockRankingData,
    isLoading: false,
    isError: false,
    error: null,
  });
  (useNotasFinales as unknown as Mock).mockReturnValue({
    data: mockNotasData,
    isLoading: false,
    isError: false,
    error: null,
  });
});

afterEach(cleanup);

describe("RankingsPage", () => {
  it("renders ranking view by default", () => {
    renderPage();
    expect(screen.getByText("Ranking de actividades")).toBeInTheDocument();
    expect(screen.getByText("Luis Martinez")).toBeInTheDocument();
    expect(screen.getByText("80%")).toBeInTheDocument();
  });

  it("toggles to notas finales view", async () => {
    const user = userEvent.setup();
    renderPage();
    const buttons = screen.getAllByRole("button");
    const notasBtn = buttons.find((b) => b.textContent === "Notas finales");
    expect(notasBtn).toBeDefined();
    if (notasBtn) await user.click(notasBtn);
    expect(screen.getByText("8.5")).toBeInTheDocument();
  });

  it("shows empty state for ranking", () => {
    (useRanking as unknown as Mock).mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      isError: false,
      error: null,
    });
    renderPage();
    expect(
      screen.getByText("Aún no hay datos de actividades aprobadas"),
    ).toBeInTheDocument();
  });

  it("shows empty state for notas finales", async () => {
    const user = userEvent.setup();
    (useNotasFinales as unknown as Mock).mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      isError: false,
      error: null,
    });
    renderPage();
    const buttons = screen.getAllByRole("button");
    const notasBtn = buttons.find((b) => b.textContent === "Notas finales");
    if (notasBtn) await user.click(notasBtn);
    expect(
      screen.getByText("Aún no hay notas finales calculadas"),
    ).toBeInTheDocument();
  });

  it("shows loading state", () => {
    (useRanking as unknown as Mock).mockReturnValue({
      data: null,
      isLoading: true,
      isError: false,
      error: null,
    });
    renderPage();
    expect(screen.getByText("Ranking de actividades")).toBeInTheDocument();
    expect(screen.queryByText("Luis Martinez")).not.toBeInTheDocument();
  });

  it("shows error state", () => {
    (useRanking as unknown as Mock).mockReturnValue({
      data: null,
      isLoading: false,
      isError: true,
      error: new Error("Error de carga"),
    });
    renderPage();
    expect(screen.getByText("Error de carga")).toBeInTheDocument();
  });
});
