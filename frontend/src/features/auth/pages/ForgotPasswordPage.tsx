import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { FormField } from "@/shared/components/FormField";
import { Input } from "@/shared/components/Input";
import { Button } from "@/shared/components/Button";
import { ErrorMessage } from "@/shared/components/ErrorMessage";
import * as authService from "@/shared/services/authService";
import type { AxiosError } from "axios";

// ---------------------------------------------------------------------------
// region: Schema
// ---------------------------------------------------------------------------

const forgot_schema = z.object({
  email: z
    .string()
    .min(1, "El email es requerido")
    .email("Ingresá un email válido"),
});

type ForgotFormData = z.infer<typeof forgot_schema>;

// ---------------------------------------------------------------------------
// endregion
// ---------------------------------------------------------------------------

export function ForgotPasswordPage() {
  const [submitting, set_submitting] = useState(false);
  const [success, set_success] = useState(false);
  const [error_message, set_error_message] = useState<string | null>(null);
  const [retry_after, set_retry_after] = useState<number | null>(null);
  const countdown_ref = useRef<ReturnType<typeof setInterval> | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotFormData>({
    resolver: zodResolver(forgot_schema),
  });

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

  useEffect(() => {
    return () => {
      if (countdown_ref.current) clearInterval(countdown_ref.current);
    };
  }, []);

  const onSubmit = async (data: ForgotFormData) => {
    set_submitting(true);
    set_error_message(null);
    set_success(false);
    set_retry_after(null);

    try {
      await authService.forgotPassword({ email: data.email });
      set_success(true);
    } catch (err: unknown) {
      const axios_err = err as AxiosError;
      if (axios_err.response?.status === 429) {
        const retry_header = axios_err.response?.headers?.["retry-after"];
        const seconds = retry_header ? parseInt(String(retry_header), 10) : 60;
        set_retry_after(isNaN(seconds) ? 60 : seconds);
      } else {
        // Generic — same message regardless of error to avoid revealing existence
        set_success(true);
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
            Recuperá tu contraseña
          </p>
        </div>

        {success && (
          <div className="mb-4 rounded-md border border-green-200 bg-green-50 p-4 text-sm text-green-800">
            Si el email está registrado, recibirás un enlace para restablecer
            tu contraseña.
          </div>
        )}

        {retry_after !== null && (
          <div className="mb-4 rounded-md border border-orange-200 bg-orange-50 p-3 text-sm text-orange-800">
            Demasiados intentos. Intentá de nuevo en{" "}
            <strong>{retry_after}</strong> segundos.
          </div>
        )}

        {error_message && !success && (
          <div className="mb-4">
            <ErrorMessage message={error_message} />
          </div>
        )}

        {!success && (
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

            <Button
              type="submit"
              className="w-full"
              is_loading={submitting}
              disabled={submitting || retry_after !== null}
            >
              Enviar enlace de recuperación
            </Button>
          </form>
        )}

        <div className="mt-6 text-center">
          <Link
            to="/login"
            className="text-sm text-brand-600 hover:text-brand-800 hover:underline"
          >
            Volver al inicio de sesión
          </Link>
        </div>
      </div>
    </div>
  );
}

