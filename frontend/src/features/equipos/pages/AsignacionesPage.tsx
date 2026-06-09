import { useState } from "react";
import { FilterableTable, type Column } from "@/shared/components/FilterableTable";
import { useAsignaciones } from "@/features/equipos/hooks/useEquipos";
import type { EquipoResponse, EquipoFilters } from "@/features/equipos/types/equipos";

const select_class =
  "block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500";

function EstadoBadge({ estado }: { estado: string }) {
  const styles: Record<string, string> = {
    vigente: "bg-green-100 text-green-800",
    vencido: "bg-red-100 text-red-800",
    proximo_vencer: "bg-yellow-100 text-yellow-800",
  };
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
        styles[estado] ?? "bg-gray-100 text-gray-800"
      }`}
    >
      {estado}
    </span>
  );
}

export function AsignacionesPage() {
  const [filters, setFilters] = useState<EquipoFilters>({});
  const { data, isLoading, isError, error } = useAsignaciones(filters);

  const columns: Column<EquipoResponse>[] = [
    { key: "usuario_id", label: "Usuario ID" },
    { key: "materia_nombre", label: "Materia", sortable: true },
    { key: "carrera_nombre", label: "Carrera", sortable: true },
    { key: "cohorte_nombre", label: "Cohorte", sortable: true },
    { key: "rol", label: "Rol", sortable: true },
    { key: "comisiones", label: "Comisiones" },
    { key: "desde", label: "Desde", sortable: true },
    { key: "hasta", label: "Hasta" },
    {
      key: "estado_vigencia",
      label: "Vigencia",
      sortable: true,
      render: (row) => <EstadoBadge estado={row.estado_vigencia} />,
    },
  ];

  const filter_bar = (
    <>
      <select
        value={filters.rol ?? ""}
        onChange={(e) =>
          setFilters((prev) => ({ ...prev, rol: e.target.value || undefined }))
        }
        className={select_class}
      >
        <option value="">Todos los roles</option>
        <option value="profesor">Profesor</option>
        <option value="tutor">Tutor</option>
        <option value="coordinador">Coordinador</option>
      </select>
      <select
        value={filters.vigente !== undefined ? String(filters.vigente) : ""}
        onChange={(e) => {
          const val = e.target.value;
          setFilters((prev) => ({
            ...prev,
            vigente: val ? val === "true" : undefined,
          }));
        }}
        className={select_class}
      >
        <option value="">Todos los estados</option>
        <option value="true">Vigentes</option>
        <option value="false">Vencidos</option>
      </select>
    </>
  );

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-gray-800">
        Asignaciones del Tenant
      </h2>
      <FilterableTable
        columns={columns}
        data={data ?? []}
        total={data?.length ?? 0}
        isLoading={isLoading}
        error={isError ? error?.message ?? "Error al cargar asignaciones" : null}
        filters={filter_bar}
        exportFileName="asignaciones.csv"
        pageSize={25}
      />
    </div>
  );
}
