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
        apellidos: usuario.apellidos ?? "",
        dni: usuario.dni ?? "",
        cuil: usuario.cuil ?? "",
        cbu: usuario.cbu ?? "",
        alias_cbu: usuario.alias_cbu ?? "",
        banco: usuario.banco ?? "",
        regional: usuario.regional ?? "",
        legajo: usuario.legajo ?? "",
        legajo_profesional: usuario.legajo_profesional ?? "",
        facturador: usuario.facturador ?? "",
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
    // Strip empty strings so optional fields stay null in backend
    const clean = Object.fromEntries(
      Object.entries(data).filter(([, v]) => v !== "")
    ) as UsuarioCreate;

    if (isEditing && id) {
      await actualizarMutation.mutateAsync({ id, payload: clean });
    } else {
      await crearMutation.mutateAsync(clean);
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
              <label htmlFor="u-email" className="block text-sm font-medium text-gray-700">
                Email
              </label>
              <input
                id="u-email"
                type="email"
                {...register("email")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
              {errors.email && (
                <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="u-nombre" className="block text-sm font-medium text-gray-700">
                Nombre
              </label>
              <input
                id="u-nombre"
                {...register("nombre")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
              {errors.nombre && (
                <p className="mt-1 text-xs text-red-600">{errors.nombre.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="u-apellidos" className="block text-sm font-medium text-gray-700">
                Apellido
              </label>
              <input
                id="u-apellidos"
                {...register("apellidos")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
              {errors.apellidos && (
                <p className="mt-1 text-xs text-red-600">{errors.apellidos.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="u-regional" className="block text-sm font-medium text-gray-700">
                Regional
              </label>
              <input
                id="u-regional"
                {...register("regional")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div>
              <label htmlFor="u-legajo" className="block text-sm font-medium text-gray-700">
                Legajo
              </label>
              <input
                id="u-legajo"
                {...register("legajo")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div>
              <label htmlFor="u-legajo-prof" className="block text-sm font-medium text-gray-700">
                Legajo profesional
              </label>
              <input
                id="u-legajo-prof"
                {...register("legajo_profesional")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="u-facturador" className="block text-sm font-medium text-gray-700">
                Facturador
              </label>
              <input
                id="u-facturador"
                {...register("facturador")}
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
              <label htmlFor="u-dni" className="block text-sm font-medium text-gray-700">
                DNI
              </label>
              <input
                id="u-dni"
                {...register("dni")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div>
              <label htmlFor="u-cuil" className="block text-sm font-medium text-gray-700">
                CUIL
              </label>
              <input
                id="u-cuil"
                {...register("cuil")}
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
              <label htmlFor="u-cbu" className="block text-sm font-medium text-gray-700">
                CBU
              </label>
              <input
                id="u-cbu"
                {...register("cbu")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div>
              <label htmlFor="u-alias-cbu" className="block text-sm font-medium text-gray-700">
                Alias CBU
              </label>
              <input
                id="u-alias-cbu"
                {...register("alias_cbu")}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div>
              <label htmlFor="u-banco" className="block text-sm font-medium text-gray-700">
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
