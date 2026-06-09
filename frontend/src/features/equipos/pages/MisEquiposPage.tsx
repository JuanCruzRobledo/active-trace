import { useState, useMemo } from "react";
import { FilterableTable, type Column } from "@/shared/components/FilterableTable";
import { useMisEquipos } from "@/features/equipos/hooks/useEquipos";
import type { EquipoResponse } from "@/features/equipos/types/equipos";

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

export function MisEquiposPage() {
  const [rolFilter, setRolFilter] = useState("");
  const [vigenteFilter, setVigenteFilter] = useState<string>("");
  const { data, isLoading, isError, error } = useMisEquipos(
    rolFilter ? { rol: rolFilter } : undefined,
  );

  const displayed = useMemo(() => {
    const raw = data ?? [];
    if (!vigenteFilter) return raw;
    return raw.filter((eq) => {
      if (vigenteFilter === "true") return eq.estado_vigencia === "Vigente";
      return eq.estado_vigencia !== "Vigente";
    });
  }, [data, vigenteFilter]);

  const columns: Column<EquipoResponse>[] = [
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
        value={rolFilter}
        onChange={(e) => setRolFilter(e.target.value)}
        className={select_class}
      >
        <option value="">Todos los roles</option>
        <option value="profesor">Profesor</option>
        <option value="tutor">Tutor</option>
        <option value="coordinador">Coordinador</option>
      </select>
      <select
        value={vigenteFilter}
        onChange={(e) => setVigenteFilter(e.target.value)}
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
      <h2 className="text-lg font-semibold text-gray-800">Mis Equipos</h2>
      <FilterableTable
        columns={columns}
        data={displayed}
        total={displayed.length}
        isLoading={isLoading}
        error={isError ? error?.message ?? "Error al cargar equipos" : null}
        filters={filter_bar}
        exportFileName="mis-equipos.csv"
        pageSize={25}
      />
    </div>
  );
}
