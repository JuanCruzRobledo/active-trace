import { useNavigate } from "react-router-dom";
import { useMisComisiones } from "@/features/comision/hooks/useMisComisiones";

export function ComisionPage() {
  const navigate = useNavigate();
  const { comisiones, isLoading, error } = useMisComisiones();

  // El `asignacion_id` se pasa como query param para que los hijos usen
  const handleClick = (item: { id: string; nombre: string; comision: string; asignacion_id: string }) => {
    navigate(`/comision/${item.id}/atrasados?asignacion_id=${item.asignacion_id}`);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-600 border-t-transparent" />
        <span className="ml-3 text-gray-500">Cargando comisiones…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-red-700">Error al cargar comisiones: {error.message}</p>
      </div>
    );
  }

  if (comisiones.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Mis Comisiones</h1>
          <p className="mt-1 text-sm text-gray-500">
            Seleccioná una comisión para gestionar sus datos
          </p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-10 text-center">
          <p className="text-gray-500">No tenés comisiones asignadas.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Mis Comisiones</h1>
        <p className="mt-1 text-sm text-gray-500">
          Seleccioná una comisión para gestionar sus datos
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {comisiones.map((c) => (
          <button
            key={`${c.id}-${c.comision}`}
            type="button"
            onClick={() => handleClick(c)}
            className="rounded-lg border bg-white p-5 text-left shadow-sm transition-colors hover:border-brand-300 hover:shadow-md"
          >
            <h2 className="text-lg font-semibold text-gray-900">{c.nombre}</h2>
            <p className="mt-1 text-sm text-gray-500">Comisión {c.comision}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
