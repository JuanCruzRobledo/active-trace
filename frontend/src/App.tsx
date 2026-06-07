import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ProtectedRoute } from "@/features/auth/components/ProtectedRoute";
import { AppLayout } from "@/features/auth/components/AppLayout";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { Verify2FAPage } from "@/features/auth/pages/Verify2FAPage";
import { Enroll2FAPage } from "@/features/auth/pages/Enroll2FAPage";
import { ForgotPasswordPage } from "@/features/auth/pages/ForgotPasswordPage";
import { ResetPasswordPage } from "@/features/auth/pages/ResetPasswordPage";
import { DashboardPage } from "@/features/auth/pages/DashboardPage";
import { NotFoundPage } from "@/features/auth/pages/NotFoundPage";

import { ComisionPage } from "@/features/comision/pages/ComisionPage";
import { ComisionLayout } from "@/features/comision/pages/ComisionLayout";
import { ImportarPage } from "@/features/comision/pages/ImportarPage";
import { UmbralPage } from "@/features/comision/pages/UmbralPage";
import { AtrasadosPage } from "@/features/comision/pages/AtrasadosPage";
import { RankingsPage } from "@/features/comision/pages/RankingsPage";
import { ReportesPage } from "@/features/comision/pages/ReportesPage";
import { ComunicacionesPage } from "@/features/comision/pages/ComunicacionesPage";

import { MonitoresPage } from "@/features/monitores/pages/MonitoresPage";

import { RequirePermission } from "@/features/auth/components/RequirePermission";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* ── Public routes ─────────────────────────────────────────── */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/2fa/verify" element={<Verify2FAPage />} />
        <Route path="/2fa/enroll" element={<Enroll2FAPage />} />
        <Route path="/forgot" element={<ForgotPasswordPage />} />
        <Route path="/reset" element={<ResetPasswordPage />} />

        {/* ── Protected routes ──────────────────────────────────────── */}
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route index element={<DashboardPage />} />

            {/* Comisión routes */}
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

            {/* Monitores route */}
            <Route
              path="monitores"
              element={
                <RequirePermission permission="atrasados:ver">
                  <MonitoresPage />
                </RequirePermission>
              }
            />

            {/* Catch-all inside protected area — shows 404 with layout */}
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Route>

        {/* ── 404 for unauthenticated users ─────────────────────────── */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}
