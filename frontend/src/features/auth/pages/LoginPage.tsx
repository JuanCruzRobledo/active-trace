import { useState, useEffect, useRef } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useAuth } from "@/shared/hooks/useAuth";
import { FormField } from "@/shared/components/FormField";
import { Input } from "@/shared/components/Input";
import { Button } from "@/shared/components/Button";
import { ErrorMessage } from "@/shared/components/ErrorMessage";
import { LoadingSpinner } from "@/shared/components/LoadingSpinner";
import type { AxiosError } from "axios";

// ---------------------------------------------------------------------------
// region: Schema
// ---------------------------------------------------------------------------

const login_schema = z.object({
  email: z
    .string()
    .min(1, "El email es requerido")
    .email("Ingresá un email válido"),
  password: z.string().min(1, "La contraseña es requerida"),
});

type LoginFormData = z.infer<typeof login_schema>;

// ---------------------------------------------------------------------------
// endregion
// ---------------------------------------------------------------------------

export function LoginPage() {
  const navigate = useNavigate();
  const [search_params] = useSearchParams();
  const { login, is_authenticated, is_loading: auth_loading } = useAuth();

  const [submitting, set_submitting] = useState(false);
  const [error_message, set_error_message] = useState<string | null>(null);
  const [retry_after, set_retry_after] = useState<number | null>(null);
  const countdown_ref = useRef<ReturnType<typeof setInterval> | null>(null);

  const redirect_to = search_params.get("redirect") ?? "/";

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(login_schema),
  });

  // If already authenticated, redirect immediately
  useEffect(() => {
    if (is_authenticated && !auth_loading) {
      navigate(redirect_to, { replace: true });
    }
  }, [is_authenticated, auth_loading, navigate, redirect_to]);

  // Countdown timer for rate-limit
  useEffect(() => {
    if (retry_after === null) return;

    countdown_ref.current = setInterval(() => {
      set_retry_after((prev) => {
        if (prev === null || prev <= 1) {
          if (countdown_ref.current) clearInterval(countdown_ref.current);
          return null;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (countdown_ref.current) clearInterval(countdown_ref.current);
    };
  }, [retry_after]);

  // Clean up error on unmount
  useEffect(() => {
    return () => {
      if (countdown_ref.current) clearInterval(countdown_ref.current);
    };
  }, []);

  const onSubmit = async (data: LoginFormData) => {
    set_submitting(true);
    set_error_message(null);
    set_retry_after(null);

    try {
      const result = await login(data.email, data.password);

      if ("twofa_required" in result) {
        // 2FA required — redirect to verification page
        navigate("/2fa/verify", {
          state: { challenge_token: result.challenge_token },
          replace: true,
        });
        return;
      }

      // Normal login — redirect
      navigate(redirect_to, { replace: true });
    } catch (err: unknown) {
      const axios_err = err as AxiosError<{ detail?: string }>;
      const status = axios_err.response?.status;

      if (status === 429) {
        const retry_header = axios_err.response?.headers?.["retry-after"];
        const seconds = retry_header ? parseInt(String(retry_header), 10) : 30;
        set_retry_after(isNaN(seconds) ? 30 : seconds);
        set_error_message(null); // We'll show the countdown message
      } else if (status === 401) {
        set_error_message("Credenciales inválidas");
      } else if (!status || status >= 500) {
        set_error_message("Error de conexión. Verificá tu conexión a internet");
      } else {
        set_error_message(
          axios_err.response?.data?.detail ?? "Ocurrió un error inesperado",
        );
      }
    } finally {
      set_submitting(false);
    }
  };

  // Show loading spinner while restoring session
  if (auth_loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingSpinner size="h-10 w-10" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        {/* Brand */}
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-brand-700">trace</h1>
          <p className="mt-1 text-sm text-gray-500">
            Iniciá sesión en tu cuenta
          </p>
        </div>

        {/* Rate-limit banner */}
        {retry_after !== null && (
          <div className="mb-4 rounded-md border border-orange-200 bg-orange-50 p-3 text-sm text-orange-800">
            Demasiados intentos. Intentá de nuevo en{" "}
            <strong>{retry_after}</strong> segundos.
          </div>
        )}

        {/* Generic error */}
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
            label="Email"
            html_for="email"
            error={errors.email?.message}
          >
            <Input
              id="email"
              type="email"
              placeholder="tu@email.com"
              autoComplete="off"
              has_error={!!errors.email}
              disabled={submitting || retry_after !== null}
              {...register("email")}
            />
          </FormField>

          <FormField
            label="Contraseña"
            html_for="password"
            error={errors.password?.message}
          >
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              autoComplete="off"
              has_error={!!errors.password}
              disabled={submitting || retry_after !== null}
              {...register("password")}
            />
          </FormField>

          <Button
            type="submit"
            className="w-full"
            is_loading={submitting}
            disabled={submitting || retry_after !== null}
          >
            Iniciar sesión
          </Button>
        </form>

        <div className="mt-6 text-center">
          <Link
            to="/forgot"
            className="text-sm text-brand-600 hover:text-brand-800 hover:underline"
          >
            ¿Olvidaste tu contraseña?
          </Link>
        </div>
      </div>
    </div>
  );
}

