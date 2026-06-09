import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/shared/components/Button";
import { Input } from "@/shared/components/Input";
import { FormField } from "@/shared/components/FormField";
import { ErrorMessage } from "@/shared/components/ErrorMessage";
import { LoadingSpinner } from "@/shared/components/LoadingSpinner";
import * as authService from "@/shared/services/authService";
import type { Enroll2FAResponse } from "@/shared/services/authService";
import type { AxiosError } from "axios";

// ---------------------------------------------------------------------------
// region: Schema
// ---------------------------------------------------------------------------

const confirm_schema = z.object({
  code: z
    .string()
    .length(6, "El código debe tener exactamente 6 dígitos")
    .regex(/^\d{6}$/, "Solo se permiten dígitos"),
});

type ConfirmFormData = z.infer<typeof confirm_schema>;

// ---------------------------------------------------------------------------
// endregion
// ---------------------------------------------------------------------------

export function Enroll2FAPage() {
  const [step, set_step] = useState<"idle" | "enrolled" | "confirmed" | "error">("idle");
  const [enroll_data, set_enroll_data] = useState<Enroll2FAResponse | null>(null);
  const [error_message, set_error_message] = useState<string | null>(null);
  const [enrolling, set_enrolling] = useState(false);
  const [confirming, set_confirming] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ConfirmFormData>({
    resolver: zodResolver(confirm_schema),
  });

  // -----------------------------------------------------------------------
// region: Enroll
  // -----------------------------------------------------------------------

  const handle_enroll = async () => {
    set_enrolling(true);
    set_error_message(null);

    try {
      const data = await authService.enroll2FA();
      set_enroll_data(data);
      set_step("enrolled");
    } catch (err: unknown) {
      const axios_err = err as AxiosError<{ detail?: string }>;
      if (axios_err.response?.status === 409) {
        set_error_message("2FA ya está configurado");
        set_step("error");
      } else {
        set_error_message("Error al configurar 2FA. Intentá de nuevo.");
      }
    } finally {
      set_enrolling(false);
    }
  };

  // -----------------------------------------------------------------------
// endregion
  // -----------------------------------------------------------------------

  // -----------------------------------------------------------------------
// region: Confirm
  // -----------------------------------------------------------------------

  const handle_confirm = async (data: ConfirmFormData) => {
    set_confirming(true);
    set_error_message(null);

    try {
      await authService.confirm2FA({ code: data.code });
      set_step("confirmed");
    } catch (err: unknown) {
      const axios_err = err as AxiosError<{ detail?: string }>;
      if (axios_err.response?.status === 400) {
        set_error_message("Código inválido. Intentá de nuevo.");
      } else {
        set_error_message("Error al confirmar. Intentá de nuevo.");
      }
    } finally {
      set_confirming(false);
    }
  };

  // -----------------------------------------------------------------------
// endregion
  // -----------------------------------------------------------------------

  // -----------------------------------------------------------------------
// region: Render helpers
  // -----------------------------------------------------------------------

  if (step === "confirmed") {
    return (
      <div className="mx-auto max-w-md py-12 text-center">
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
          2FA activado correctamente
        </h2>
        <p className="mt-2 text-sm text-gray-500">
          A partir del próximo inicio de sesión se te solicitará un código de
          verificación.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md py-12">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">
        Autenticación de dos factores
      </h1>

      {error_message && (
        <div className="mb-4">
          <ErrorMessage message={error_message} />
        </div>
      )}

      {step === "idle" && (
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Configurá la autenticación de dos factores para proteger tu cuenta.
            Vas a necesitar una aplicación como Google Authenticator o Authy.
          </p>
          <Button onClick={handle_enroll} is_loading={enrolling}>
            Configurar 2FA
          </Button>
        </div>
      )}

      {step === "enrolled" && enroll_data && (
        <div className="space-y-6">
          {/* QR Code */}
          <div className="flex justify-center">
            {enroll_data.qr_code ? (
              <img
                src={`data:image/png;base64,${enroll_data.qr_code}`}
                alt="Código QR para 2FA"
                className="h-48 w-48 rounded border"
              />
            ) : (
              <LoadingSpinner size="h-12 w-12" />
            )}
          </div>

          {/* Secret code */}
          <div className="rounded-md bg-gray-50 p-4 text-center">
            <p className="mb-1 text-xs text-gray-500">
              O ingresá este código manualmente:
            </p>
            <code className="select-all rounded bg-gray-200 px-3 py-1 font-mono text-sm">
              {enroll_data.secret}
            </code>
          </div>

          <p className="text-sm text-gray-600">
            Escaneá el código QR con tu aplicación de autenticación y luego
            ingresá el código de 6 dígitos para confirmar.
          </p>

          <form
            onSubmit={handleSubmit(handle_confirm)}
            className="space-y-4"
            autoComplete="off"
          >
            <FormField
              label="Código de confirmación"
              html_for="confirm-code"
              error={errors.code?.message}
            >
              <Input
                id="confirm-code"
                type="text"
                inputMode="numeric"
                maxLength={6}
                placeholder="••••••"
                className="text-center text-2xl tracking-[0.5em]"
                has_error={!!errors.code}
                disabled={confirming}
                {...register("code")}
              />
            </FormField>

            <Button
              type="submit"
              className="w-full"
              is_loading={confirming}
              disabled={confirming}
            >
              Confirmar
            </Button>
          </form>
        </div>
      )}

      {step === "error" && (
        <Button variant="secondary" onClick={() => set_step("idle")}>
          Intentar de nuevo
        </Button>
      )}
    </div>
  );
}

