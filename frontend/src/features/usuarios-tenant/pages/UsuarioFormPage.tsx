import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  useUsuarioTenantById,
  useCrearUsuarioTenant,
  useActualizarUsuarioTenant,
} from "@/features/usuarios-tenant/hooks/useUsuariosTenant";
import {
  UsuarioCreateSchema,
} from "@/features/usuarios-tenant/types/usuarios";
import type { UsuarioCreate } from "@/features/usuarios-tenant/types/usuarios";
import { LoadingSpinner } from "@/shared/components/LoadingSpinner";

const ROL_OPTIONS = ["TUTOR", "NEXO", "COORDINADOR", "ADMIN", "SOPORTE"];
const MODALIDAD_OPTIONS = ["presencial", "virtual", "mixta"];

export function UsuarioFormPage() {
  const { id } = useParams<{ id: string }>();
  const isEditing = !!id;
  const navigate = useNavigate();

  const { data: usuario, isLoading } = useUsuarioTenantById(id);
  const crearMutation = useCrearUsuarioTenant();
  const actualizarMutation = useActualizarUsuarioTenant();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<UsuarioCreate>({
    resolver: zodResolver(UsuarioCreateSchema),
  });

  useEffect(() => {
    if (usuario) {
      reset({
        email: usuario.email,
        nombre: usuario.nombre,
        apellido: usuario.apellido ?? "",
        rol: usuario.rol ?? "",
        modalidad: usuario.modalidad ?? "",
        cuit: usuario.cuit ?? "",
        condicion_fiscal: usuario.condicion_fiscal ?? "",
        cbu: usuario.cbu ?? "",
        alias: usuario.alias ?? "",
        banco: usuario.banco ?? "",
        regional: usuario.regional ?? "",
      });
    }
  }, [usuario, reset]);

  if (isEditing && isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <LoadingSpinner size="h-8 w-8" />
      </div>
    );
  }

  async function onSubmit(data: UsuarioCreate) {
    if (isEditing && id) {
      await actualizarMutation.mutateAsync({ id, payload: data });
    } else {
      await crearMutation.mutateAsync(data);
    }
    navigate("/usuarios");
  }

  const isPending = crearMutation.isPending || actualizarMutation.isPending;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          {isEditing ? "Editar usuario" : "Nuevo usuario"}
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Datos del usuario del sistema
        </p>
      </div>

      <form
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-6 rounded-lg border bg-white p-6 shadow-sm"
      >
        {/* Datos básicos */}
        <section className="space-y-4">
          <h2 className="text-base font-semibold text-gray-800">Datos básicos</h2>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label
                htmlFor="u-email"
                className="block text-sm font-medium text-gray-700"
              >
                Email
              </label>
              <input
                id="u-email"
                type="email"
                {...register("email")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
              {errors.email && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.email.message}
                </p>
              )}
            </div>

            <div>
              <label
                htmlFor="u-nombre"
                className="block text-sm font-medium text-gray-700"
              >
                Nombre
              </label>
              <input
                id="u-nombre"
                {...register("nombre")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
              {errors.nombre && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.nombre.message}
                </p>
              )}
            </div>

            <div>
              <label
                htmlFor="u-apellido"
                className="block text-sm font-medium text-gray-700"
              >
                Apellido
              </label>
              <input
                id="u-apellido"
                {...register("apellido")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div>
              <label
                htmlFor="u-rol"
                className="block text-sm font-medium text-gray-700"
              >
                Rol
              </label>
              <select
                id="u-rol"
                {...register("rol")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                <option value="">Sin rol</option>
                {ROL_OPTIONS.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label
                htmlFor="u-modalidad"
                className="block text-sm font-medium text-gray-700"
              >
                Modalidad
              </label>
              <select
                id="u-modalidad"
                {...register("modalidad")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                <option value="">Sin especificar</option>
                {MODALIDAD_OPTIONS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label
                htmlFor="u-regional"
                className="block text-sm font-medium text-gray-700"
              >
                Regional
              </label>
              <input
                id="u-regional"
                {...register("regional")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>
        </section>

        {/* Datos fiscales */}
        <section className="space-y-4">
          <h2 className="text-base font-semibold text-gray-800">Datos fiscales</h2>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label
                htmlFor="u-cuit"
                className="block text-sm font-medium text-gray-700"
              >
                CUIT
              </label>
              <input
                id="u-cuit"
                {...register("cuit")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div>
              <label
                htmlFor="u-condicion"
                className="block text-sm font-medium text-gray-700"
              >
                Condición fiscal
              </label>
              <input
                id="u-condicion"
                {...register("condicion_fiscal")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>
        </section>

        {/* Datos bancarios */}
        <section className="space-y-4">
          <h2 className="text-base font-semibold text-gray-800">Datos bancarios</h2>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label
                htmlFor="u-cbu"
                className="block text-sm font-medium text-gray-700"
              >
                CBU
              </label>
              <input
                id="u-cbu"
                {...register("cbu")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div>
              <label
                htmlFor="u-alias"
                className="block text-sm font-medium text-gray-700"
              >
                Alias
              </label>
              <input
                id="u-alias"
                {...register("alias")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div>
              <label
                htmlFor="u-banco"
                className="block text-sm font-medium text-gray-700"
              >
                Banco
              </label>
              <input
                id="u-banco"
                {...register("banco")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>
        </section>

        <div className="flex justify-end gap-3 border-t pt-4">
          <button
            type="button"
            onClick={() => navigate("/usuarios")}
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={isPending}
            className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {isPending ? "Guardando..." : isEditing ? "Actualizar" : "Crear usuario"}
          </button>
        </div>
      </form>
    </div>
  );
}
