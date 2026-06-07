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
import { EquiposLayout } from "@/features/equipos/pages/EquiposLayout";
import { MisEquiposPage } from "@/features/equipos/pages/MisEquiposPage";
import { AsignacionesPage } from "@/features/equipos/pages/AsignacionesPage";
import { AsignacionMasivaPage } from "@/features/equipos/pages/AsignacionMasivaPage";
import { ClonarEquipoPage } from "@/features/equipos/pages/ClonarEquipoPage";
import { VigenciaEquipoPage } from "@/features/equipos/pages/VigenciaEquipoPage";
import { ExportarEquipoPage } from "@/features/equipos/pages/ExportarEquipoPage";
import { AvisosListPage } from "@/features/avisos/pages/AvisosListPage";
import { AvisoFormPage } from "@/features/avisos/pages/AvisoFormPage";
import { AvisoDetailPage } from "@/features/avisos/pages/AvisoDetailPage";
import { GuardiasPage } from "@/features/guardias/pages/GuardiasPage";
import { ProgramasPage } from "@/features/programas/pages/ProgramasPage";
import { FechasAcademicasPage } from "@/features/fechas-academicas/pages/FechasAcademicasPage";
import { SetupCuatrimestreWizard } from "@/features/setup-cuatrimestre/pages/SetupCuatrimestreWizard";

import { RequirePermission } from "@/features/auth/components/RequirePermission";

import { TareasLayout } from "@/features/tareas/pages/TareasLayout";
import { MisTareasPage } from "@/features/tareas/pages/MisTareasPage";
import { AsignarTareaPage } from "@/features/tareas/pages/AsignarTareaPage";
import { TareasAdminPage } from "@/features/tareas/pages/TareasAdminPage";

import { EncuentrosAdminPage } from "@/features/encuentros/pages/EncuentrosAdminPage";

import { ColoquiosLayout } from "@/features/coloquios/pages/ColoquiosLayout";
import { ColoquiosPanelPage } from "@/features/coloquios/pages/ColoquiosPanelPage";
import { ConvocatoriaListPage } from "@/features/coloquios/pages/ConvocatoriaListPage";
import { ConvocatoriaFormPage } from "@/features/coloquios/pages/ConvocatoriaFormPage";
import { ColoquiosAdminPage } from "@/features/coloquios/pages/ColoquiosAdminPage";

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

            {/* ── Equipos Docentes ────────────────────────────────────── */}
            <Route
              path="equipos"
              element={
                <RequirePermission permission="equipos:ver">
                  <EquiposLayout />
                </RequirePermission>
              }
            >
              <Route index element={<Navigate to="mis-equipos" replace />} />
              <Route path="mis-equipos" element={<MisEquiposPage />} />
              <Route
                path="asignaciones"
                element={
                  <RequirePermission permission="equipos:asignar">
                    <AsignacionesPage />
                  </RequirePermission>
                }
              />
              <Route
                path="asignacion-masiva"
                element={
                  <RequirePermission permission="equipos:asignar">
                    <AsignacionMasivaPage />
                  </RequirePermission>
                }
              />
              <Route
                path="clonar"
                element={
                  <RequirePermission permission="equipos:asignar">
                    <ClonarEquipoPage />
                  </RequirePermission>
                }
              />
              <Route
                path="vigencia"
                element={
                  <RequirePermission permission="equipos:asignar">
                    <VigenciaEquipoPage />
                  </RequirePermission>
                }
              />
              <Route
                path="exportar"
                element={
                  <RequirePermission permission="equipos:ver">
                    <ExportarEquipoPage />
                  </RequirePermission>
                }
              />
            </Route>

            {/* ── Avisos ──────────────────────────────────────────────── */}
            <Route
              path="avisos"
              element={
                <RequirePermission permission="avisos:publicar">
                  <AvisosListPage />
                </RequirePermission>
              }
            />
            <Route
              path="avisos/nuevo"
              element={
                <RequirePermission permission="avisos:publicar">
                  <AvisoFormPage />
                </RequirePermission>
              }
            />
            <Route
              path="avisos/:id"
              element={
                <RequirePermission permission="avisos:publicar">
                  <AvisoDetailPage />
                </RequirePermission>
              }
            />
            <Route
              path="avisos/:id/editar"
              element={
                <RequirePermission permission="avisos:publicar">
                  <AvisoFormPage />
                </RequirePermission>
              }
            />

            {/* ── Tareas ──────────────────────────────────────────────── */}
            <Route path="tareas" element={<TareasLayout />}>
              <Route index element={<Navigate to="mis-tareas" replace />} />
              <Route path="mis-tareas" element={<MisTareasPage />} />
              <Route
                path="asignar"
                element={
                  <RequirePermission permission="tareas:asignar">
                    <AsignarTareaPage />
                  </RequirePermission>
                }
              />
              <Route
                path="admin"
                element={
                  <RequirePermission permission="tareas:asignar">
                    <TareasAdminPage />
                  </RequirePermission>
                }
              />
            </Route>

            {/* ── Encuentros ──────────────────────────────────────────── */}
            <Route
              path="encuentros"
              element={
                <RequirePermission permission="encuentros:ver">
                  <EncuentrosAdminPage />
                </RequirePermission>
              }
            />

            {/* ── Coloquios ───────────────────────────────────────────── */}
            <Route
              path="coloquios"
              element={
                <RequirePermission permission="coloquios:gestionar">
                  <ColoquiosLayout />
                </RequirePermission>
              }
            >
              <Route index element={<Navigate to="panel" replace />} />
              <Route path="panel" element={<ColoquiosPanelPage />} />
              <Route path="convocatorias" element={<ConvocatoriaListPage />} />
              <Route path="convocatorias/nueva" element={<ConvocatoriaFormPage />} />
              <Route path="admin" element={<ColoquiosAdminPage />} />
            </Route>

            {/* ── Guardias ────────────────────────────────────────────── */}
            <Route
              path="guardias"
              element={
                <RequirePermission permission="guardias:registrar">
                  <GuardiasPage />
                </RequirePermission>
              }
            />

            {/* ── Programas (Estructura) ──────────────────────────────── */}
            <Route
              path="programas"
              element={
                <RequirePermission permission="estructura:gestionar">
                  <ProgramasPage />
                </RequirePermission>
              }
            />

            {/* ── Fechas Académicas ────────────────────────────────────── */}
            <Route
              path="fechas-academicas"
              element={
                <RequirePermission permission="estructura:gestionar">
                  <FechasAcademicasPage />
                </RequirePermission>
              }
            />

            {/* ── Setup Cuatrimestre ──────────────────────────────────── */}
            <Route
              path="setup-cuatrimestre"
              element={
                <RequirePermission permission="equipos:asignar">
                  <SetupCuatrimestreWizard />
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
