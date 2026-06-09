import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
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

const reset_schema = z
  .object({
    new_password: z
      .string()
      .min(12, "La contraseña debe tener al menos 12 caracteres")
      .regex(/[A-Z]/, "Debe contener al menos 1 mayúscula")
      .regex(/[a-z]/, "Debe contener al menos 1 minúscula")
      .regex(/[0-9]/, "Debe contener al menos 1 dígito"),
    confirm_password: z.string().min(1, "Confirmá la contraseña"),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Las contraseñas no coinciden",
    path: ["confirm_password"],
  });

type ResetFormData = z.infer<typeof reset_schema>;

// ---------------------------------------------------------------------------
// endregion
// ---------------------------------------------------------------------------

export function ResetPasswordPage() {
  const [search_params] = useSearchParams();
  const token = search_params.get("token");

  const [submitting, set_submitting] = useState(false);
  const [error_message, set_error_message] = useState<string | null>(null);
  const [success, set_success] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetFormData>({
    resolver: zodResolver(reset_schema),
  });

  const onSubmit = async (data: ResetFormData) => {
    if (!token) return;

    set_submitting(true);
    set_error_message(null);

    try {
      await authService.resetPassword({
        token,
        new_password: data.new_password,
      });
      set_success(true);
    } catch (err: unknown) {
      const axios_err = err as AxiosError<{ detail?: string }>;
      const detail = axios_err.response?.data?.detail ?? "";

      if (detail.includes("expired") || detail.includes("expirado")) {
        set_error_message(
          "El enlace de recuperación expiró. Solicitá uno nuevo.",
        );
      } else if (
        detail.includes("already used") ||
        detail.includes("ya usado")
      ) {
        set_error_message(
          "Este enlace ya fue usado. Solicitá uno nuevo.",
        );
      } else if (detail.includes("Invalid") || detail.includes("inválido")) {
        set_error_message("Enlace inválido. Solicitá uno nuevo.");
      } else {
        set_error_message("Ocurrió un error. Intentá de nuevo.");
      }
    } finally {
      set_submitting(false);
    }
  };

  // No token in URL
  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
        <div className="w-full max-w-sm text-center">
          <h1 className="mb-4 text-2xl font-bold text-gray-900">
            Enlace inválido
          </h1>
          <p className="mb-6 text-sm text-gray-600">
            Solicitá una nueva recuperación de contraseña.
          </p>
          <Link
            to="/forgot"
            className="text-sm text-brand-600 hover:text-brand-800 hover:underline"
          >
            Solicitar recuperación
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-brand-700">trace</h1>
          <p className="mt-2 text-sm text-gray-500">
            Establecé tu nueva contraseña
          </p>
        </div>

        {success && (
          <div className="text-center">
            <div className="mb-4 inline-flex h-14 w-14 items-center justify-center rounded-full bg-green-100">
              <svg
                className="h-8 w-8 text-green-600"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4.5 12.75l6 6 9-13.5"
                />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-gray-900">
              Contraseña actualizada correctamente
            </h2>
            <p className="mt-2 text-sm text-gray-500">
              Ya podés iniciar sesión con tu nueva contraseña.
            </p>
            <Link
              to="/login"
              className="mt-6 inline-block rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
            >
              Ir a iniciar sesión
            </Link>
          </div>
        )}

        {!success && (
          <>
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
                label="Nueva contraseña"
                html_for="new_password"
                error={errors.new_password?.message}
                hint="Mínimo 12 caracteres, 1 mayúscula, 1 minúscula, 1 dígito"
              >
                <Input
                  id="new_password"
                  type="password"
                  placeholder="••••••••••••"
                  autoComplete="new-password"
                  has_error={!!errors.new_password}
                  disabled={submitting}
                  {...register("new_password")}
                />
              </FormField>

              <FormField
                label="Confirmar contraseña"
                html_for="confirm_password"
                error={errors.confirm_password?.message}
              >
                <Input
                  id="confirm_password"
                  type="password"
                  placeholder="••••••••••••"
                  autoComplete="new-password"
                  has_error={!!errors.confirm_password}
                  disabled={submitting}
                  {...register("confirm_password")}
                />
              </FormField>

              <Button
                type="submit"
                className="w-full"
                is_loading={submitting}
                disabled={submitting}
              >
                Restablecer contraseña
              </Button>
            </form>

            <div className="mt-6 text-center">
              <Link
                to="/login"
                className="text-sm text-gray-500 hover:text-gray-700 hover:underline"
              >
                Volver al inicio de sesión
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

