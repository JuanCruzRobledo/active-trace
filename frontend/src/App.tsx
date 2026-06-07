import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ProtectedRoute } from "@/features/auth/components/ProtectedRoute";
import { AppLayout } from "@/features/auth/components/AppLayout";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { Verify2FAPage } from "@/features/auth/pages/Verify2FAPage";
import { Enroll2FAPage } from "@/features/auth/pages/Enroll2FAPage";
import { ForgotPasswordPage } from "@/features/auth/pages/ForgotPasswordPage";
import { ResetPasswordPage } from "@/features/auth/pages/ResetPasswordPage";
import { DashboardPage } from "@/features/auth/pages/DashboardPage";
import { NotFoundPage } from "@/features/auth/pages/NotFoundPage";

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
            {/* Future feature routes will be added here in C-22+C-23 */}

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
