import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { vi, describe, it, expect } from "vitest";

import { ProtectedRoute } from "@/features/auth/components/ProtectedRoute";
import { RequirePermission } from "@/features/auth/components/RequirePermission";
import { AppLayout } from "@/features/auth/components/AppLayout";
import { DashboardPage } from "@/features/auth/pages/DashboardPage";
import { ComisionPage } from "@/features/comision/pages/ComisionPage";
import { ComisionLayout } from "@/features/comision/pages/ComisionLayout";
import { ImportarPage } from "@/features/comision/pages/ImportarPage";
import { UmbralPage } from "@/features/comision/pages/UmbralPage";
import { AtrasadosPage } from "@/features/comision/pages/AtrasadosPage";
import { RankingsPage } from "@/features/comision/pages/RankingsPage";
import { ReportesPage } from "@/features/comision/pages/ReportesPage";
import { ComunicacionesPage } from "@/features/comision/pages/ComunicacionesPage";
import { MonitoresPage } from "@/features/monitores/pages/MonitoresPage";

vi.mock("@/features/auth/components/ProtectedRoute", () => ({
  ProtectedRoute: () => <Outlet />,
}));

vi.mock("@/features/auth/components/RequirePermission", () => ({
  RequirePermission: ({
    children,
  }: {
    permission: string;
    children?: React.ReactNode;
  }) => <>{children}</>,
}));

vi.mock("@/shared/hooks/useAuth", () => ({
  useAuth: () => ({
    user: {
      id: "u1",
      email: "test@test.com",
      nombre: "Test User",
      roles: ["PROFESOR"],
      permisos: [
        "calificaciones:importar",
        "atrasados:ver",
        "analisis:ver",
        "equipos:asignar",
      ],
    },
    is_loading: false,
    is_authenticated: true,
    permissions: [
      "calificaciones:importar",
      "atrasados:ver",
      "analisis:ver",
      "equipos:asignar",
    ],
    logout: vi.fn(),
    login: vi.fn(),
    complete2FA: vi.fn(),
    set_session_from_tokens: vi.fn(),
  }),
  AuthProvider: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/features/auth/components/AppLayout", () => ({
  AppLayout: () => (
    <div data-testid="app-layout">
      <nav data-testid="sidebar">
        <a href="/">Inicio</a>
        <a href="/comision">Mis Comisiones</a>
        <a href="/monitores">Monitores</a>
      </nav>
      <main data-testid="page-content">
        <Outlet />
      </main>
    </div>
  ),
}));

vi.mock("@/features/auth/pages/DashboardPage", () => ({
  DashboardPage: () => <div data-testid="dashboard-page">Dashboard</div>,
}));

vi.mock("@/features/comision/pages/ComisionPage", () => ({
  ComisionPage: () => <div data-testid="comision-page">Comisiones</div>,
}));

vi.mock("@/features/comision/pages/ComisionLayout", () => ({
  ComisionLayout: () => (
    <div data-testid="comision-layout">
      <nav data-testid="sub-nav">
        <a href="/comision/mat-001/atrasados">Atrasados</a>
        <a href="/comision/mat-001/rankings">Rankings</a>
        <a href="/comision/mat-001/reportes">Reportes</a>
        <a href="/comision/mat-001/importar">Importar</a>
        <a href="/comision/mat-001/umbral">Umbral</a>
        <a href="/comision/mat-001/comunicaciones">Comunicaciones</a>
      </nav>
      <Outlet />
    </div>
  ),
}));

vi.mock("@/features/comision/pages/ImportarPage", () => ({
  ImportarPage: () => <div data-testid="importar-page">Importar</div>,
}));

vi.mock("@/features/comision/pages/UmbralPage", () => ({
  UmbralPage: () => <div data-testid="umbral-page">Umbral</div>,
}));

vi.mock("@/features/comision/pages/AtrasadosPage", () => ({
  AtrasadosPage: () => <div data-testid="atrasados-page">Atrasados</div>,
}));

vi.mock("@/features/comision/pages/RankingsPage", () => ({
  RankingsPage: () => <div data-testid="rankings-page">Rankings</div>,
}));

vi.mock("@/features/comision/pages/ReportesPage", () => ({
  ReportesPage: () => <div data-testid="reportes-page">Reportes</div>,
}));

vi.mock("@/features/comision/pages/ComunicacionesPage", () => ({
  ComunicacionesPage: () => (
    <div data-testid="comunicaciones-page">Comunicaciones</div>
  ),
}));

vi.mock("@/features/monitores/pages/MonitoresPage", () => ({
  MonitoresPage: () => <div data-testid="monitores-page">Monitores</div>,
}));

function TestRoutes() {
  return (
    <Routes>
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route
            path="comision"
            element={
              <RequirePermission permission="calificaciones:importar">
                <ComisionPage />
              </RequirePermission>
            }
          />
          <Route
            path="comision/:materiaId"
            element={
              <RequirePermission permission="calificaciones:importar">
                <ComisionLayout />
              </RequirePermission>
            }
          >
            <Route index element={<Navigate to="atrasados" replace />} />
            <Route path="importar" element={<ImportarPage />} />
            <Route path="umbral" element={<UmbralPage />} />
            <Route path="atrasados" element={<AtrasadosPage />} />
            <Route path="rankings" element={<RankingsPage />} />
            <Route path="reportes" element={<ReportesPage />} />
            <Route path="comunicaciones" element={<ComunicacionesPage />} />
          </Route>
          <Route
            path="monitores"
            element={
              <RequirePermission permission="analisis:ver">
                <MonitoresPage />
              </RequirePermission>
            }
          />
        </Route>
      </Route>
    </Routes>
  );
}

function renderAppAt(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <TestRoutes />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("App Routing", () => {
  it("renders dashboard at /", () => {
    renderAppAt("/");
    expect(screen.getByTestId("app-layout")).toBeInTheDocument();
    expect(screen.getByTestId("dashboard-page")).toBeInTheDocument();
  });

  it("renders sidebar with Comisiones and Monitores links", () => {
    renderAppAt("/");
    expect(screen.getByText("Inicio")).toBeInTheDocument();
    expect(screen.getByText("Mis Comisiones")).toBeInTheDocument();
    expect(screen.getByText("Monitores")).toBeInTheDocument();
  });

  it("renders ComisionPage at /comision", () => {
    renderAppAt("/comision");
    expect(screen.getByTestId("comision-page")).toBeInTheDocument();
  });

  it("renders AtrasadosPage at /comision/:id/atrasados", () => {
    renderAppAt("/comision/mat-001/atrasados");
    expect(screen.getByTestId("atrasados-page")).toBeInTheDocument();
  });

  it("renders RankingsPage at /comision/:id/rankings", () => {
    renderAppAt("/comision/mat-001/rankings");
    expect(screen.getByTestId("rankings-page")).toBeInTheDocument();
  });

  it("renders ReportesPage at /comision/:id/reportes", () => {
    renderAppAt("/comision/mat-001/reportes");
    expect(screen.getByTestId("reportes-page")).toBeInTheDocument();
  });

  it("renders ImportarPage at /comision/:id/importar", () => {
    renderAppAt("/comision/mat-001/importar");
    expect(screen.getByTestId("importar-page")).toBeInTheDocument();
  });

  it("renders UmbralPage at /comision/:id/umbral", () => {
    renderAppAt("/comision/mat-001/umbral");
    expect(screen.getByTestId("umbral-page")).toBeInTheDocument();
  });

  it("renders ComunicacionesPage at /comision/:id/comunicaciones", () => {
    renderAppAt("/comision/mat-001/comunicaciones");
    expect(screen.getByTestId("comunicaciones-page")).toBeInTheDocument();
  });

  it("renders MonitoresPage at /monitores", () => {
    renderAppAt("/monitores");
    expect(screen.getByTestId("monitores-page")).toBeInTheDocument();
  });

  it("renders ComisionLayout with sub-navigation at /comision/:id/importar", () => {
    renderAppAt("/comision/mat-001/importar");
    expect(screen.getByTestId("sub-nav")).toBeInTheDocument();
    expect(screen.getByText("Atrasados")).toBeInTheDocument();
    expect(screen.getByText("Rankings")).toBeInTheDocument();
    expect(screen.getByText("Reportes")).toBeInTheDocument();
    expect(screen.getByTestId("sub-nav")).toHaveTextContent("Importar");
    expect(screen.getByText("Umbral")).toBeInTheDocument();
    expect(screen.getByText("Comunicaciones")).toBeInTheDocument();
  });
});
