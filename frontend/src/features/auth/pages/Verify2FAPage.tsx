import { useState, useEffect } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useAuth } from "@/shared/hooks/useAuth";
import { FormField } from "@/shared/components/FormField";
import { Input } from "@/shared/components/Input";
import { Button } from "@/shared/components/Button";
import { ErrorMessage } from "@/shared/components/ErrorMessage";
import type { AxiosError } from "axios";

// ---------------------------------------------------------------------------
// region: Schema
// ---------------------------------------------------------------------------

const verify_schema = z.object({
  code: z
    .string()
    .length(6, "El código debe tener exactamente 6 dígitos")
    .regex(/^\d{6}$/, "Solo se permiten dígitos"),
});

type VerifyFormData = z.infer<typeof verify_schema>;

// ---------------------------------------------------------------------------
// endregion
// ---------------------------------------------------------------------------

interface LocationState {
  challenge_token?: string;
}

export function Verify2FAPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { complete2FA } = useAuth();

  const [submitting, set_submitting] = useState(false);
  const [error_message, set_error_message] = useState<string | null>(null);

  const state = location.state as LocationState | null;
  const challenge_token = state?.challenge_token;

  // Redirect to login if no challenge token
  useEffect(() => {
    if (!challenge_token) {
      navigate("/login", { replace: true });
    }
  }, [challenge_token, navigate]);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<VerifyFormData>({
    resolver: zodResolver(verify_schema),
  });

  const onSubmit = async (data: VerifyFormData) => {
    if (!challenge_token) return;

    set_submitting(true);
    set_error_message(null);

    try {
      await complete2FA(challenge_token, data.code);
      navigate("/", { replace: true });
    } catch (err: unknown) {
      const axios_err = err as AxiosError<{ detail?: string }>;
      const detail = axios_err.response?.data?.detail ?? "";

      if (detail.includes("expirado") || detail.includes("expired")) {
        set_error_message(
          "El código expiró. Por favor, iniciá sesión de nuevo.",
        );
        setTimeout(() => navigate("/login", { replace: true }), 2000);
      } else if (
        detail.includes("ya usado") ||
        detail.includes("already used")
      ) {
        set_error_message(
          "Este código ya fue usado. Iniciá sesión nuevamente.",
        );
        setTimeout(() => navigate("/login", { replace: true }), 2000);
      } else {
        set_error_message("Código incorrecto. Intentá de nuevo.");
      }
    } finally {
      set_submitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-brand-700">trace</h1>
          <p className="mt-2 text-sm text-gray-500">
            Ingresá el código de 6 dígitos de tu aplicación de autenticación
          </p>
        </div>

        {error_message && (
          <div className="mb-4">
            <ErrorMessage message={error_message} />
          </div>
        )}

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="space-y-4"
          autoComplete="off"
        >
          <FormField
            label="Código de verificación"
            html_for="code"
            error={errors.code?.message}
          >
            <Input
              id="code"
              type="text"
              inputMode="numeric"
              maxLength={6}
              placeholder="••••••"
              className="text-center text-2xl tracking-[0.5em]"
              autoFocus
              has_error={!!errors.code}
              disabled={submitting}
              {...register("code")}
            />
          </FormField>

          <Button
            type="submit"
            className="w-full"
            is_loading={submitting}
            disabled={submitting}
          >
            Verificar
          </Button>
        </form>

        <div className="mt-6 text-center">
          <Link
            to="/login"
            className="text-sm text-gray-500 hover:text-gray-700 hover:underline"
            onClick={() => {
              // Clear any challenge data by navigating cleanly
            }}
          >
            Volver al inicio de sesión
          </Link>
        </div>
      </div>
    </div>
  );
}

