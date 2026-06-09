import { useAuth } from "@/shared/hooks/useAuth";

export function DashboardPage() {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Inicio</h1>
        <p className="mt-1 text-sm text-gray-500">
          Bienvenido, {user?.nombre ?? "usuario"}
        </p>
      </div>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {/* Placeholder cards — will be populated in future changes */}
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">Mis Comisiones</h2>
          <p className="mt-2 text-sm text-gray-500">
            Accedé a tus comisiones y estudiantes.
          </p>
        </div>
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">Avisos</h2>
          <p className="mt-2 text-sm text-gray-500">
            Consultá los avisos y novedades.
          </p>
        </div>
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900">
            Comunicaciones
          </h2>
          <p className="mt-2 text-sm text-gray-500">
            Enviá y recibí comunicaciones.
          </p>
        </div>
      </div>
    </div>
  );
}

