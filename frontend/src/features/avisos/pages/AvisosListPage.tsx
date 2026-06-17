import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FilterableTable, type Column } from "@/shared/components/FilterableTable";
import { Button } from "@/shared/components/Button";
import { useAvisos, useEliminarAviso } from "@/features/avisos/hooks/useAvisos";
import type { AvisoResponse, AvisoFilters } from "@/features/avisos/types/avisos";
import { ConfirmDialog } from "@/shared/components/ConfirmDialog";
import { useAuth } from "@/shared/hooks/useAuth";

const select_class =
  "block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500";

function SeveridadBadge({ severidad }: { severidad: string }) {
  const styles: Record<string, string> = {
    "Crítico": "bg-red-100 text-red-800",
    "Advertencia": "bg-yellow-100 text-yellow-800",
    "Info": "bg-blue-100 text-blue-800",
  };
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
        styles[severidad] ?? "bg-gray-100 text-gray-800"
      }`}
    >
      {severidad}
    </span>
  );
}

function ActivoBadge({ activo }: { activo: boolean }) {
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
        activo
          ? "bg-green-100 text-green-800"
          : "bg-gray-100 text-gray-400"
      }`}
    >
      {activo ? "Activo" : "Inactivo"}
    </span>
  );
}

export function AvisosListPage() {
  const navigate = useNavigate();
  const { permissions } = useAuth();
  const puede_gestionar = permissions.includes("avisos:gestionar");
  const [filters, setFilters] = useState<AvisoFilters>({});
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const { data, isLoading, isError, error } = useAvisos(filters);
  
  const eliminarAviso = useEliminarAviso();

  const columns: Column<AvisoResponse>[] = [
    {
      key: "titulo",
      label: "Título",
      sortable: true,
      render: (row) => (
        <Link
          to={`/avisos/${row.id}`}
          className="font-medium text-brand-600 hover:text-brand-800"
        >
          {row.titulo}
        </Link>
      ),
    },
    { key: "alcance", label: "Alcance", sortable: true },
    {
      key: "severidad",
      label: "Severidad",
      sortable: true,
      render: (row) => <SeveridadBadge severidad={row.severidad} />,
    },
    { key: "inicio_en", label: "Inicio", sortable: true },
    { key: "fin_en", label: "Fin", sortable: true },
    { key: "requiere_ack", label: "Requiere ACK" },
    {
      key: "porcentaje_ack",
      label: "% ACK",
      sortable: true,
      render: (row) => `${row.porcentaje_ack}%`,
    },
    {
      key: "activo",
      label: "Estado",
      sortable: true,
      render: (row) => <ActivoBadge activo={row.activo} />,
    },
    ...(puede_gestionar
      ? [
          {
            key: "id" as const,
            label: "Acciones",
            render: (row: AvisoResponse) => (
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => navigate(`/avisos/${row.id}/editar`)}
                  className="text-sm text-brand-600 hover:text-brand-800"
                >
                  Editar
                </button>
                <button
                  type="button"
                  onClick={() => setDeleteId(row.id)}
                  className="text-sm text-red-600 hover:text-red-800"
                >
                  Eliminar
                </button>
              </div>
            ),
          },
        ]
      : []),
  ];

  const filter_bar = (
    <>
      <select
        value={filters.alcance ?? ""}
        onChange={(e) =>
          setFilters((prev) => ({
            ...prev,
            alcance: e.target.value || undefined,
          }))
        }
        className={select_class}
      >
        <option value="">Todos los alcances</option>
        <option value="Global">Global</option>
        <option value="PorMateria">Por Materia</option>
        <option value="PorCohorte">Por Cohorte</option>
        <option value="PorRol">Por Rol</option>
      </select>
      <select
        value={filters.severidad ?? ""}
        onChange={(e) =>
          setFilters((prev) => ({
            ...prev,
            severidad: e.target.value || undefined,
          }))
        }
        className={select_class}
      >
        <option value="">Todas las severidades</option>
        <option value="Info">Info</option>
        <option value="Advertencia">Advertencia</option>
        <option value="Crítico">Crítico</option>
      </select>
      <select
        value={filters.activo !== undefined ? String(filters.activo) : ""}
        onChange={(e) => {
          const val = e.target.value;
          setFilters((prev) => ({
            ...prev,
            activo: val ? val === "true" : undefined,
          }));
        }}
        className={select_class}
      >
        <option value="">Activos e inactivos</option>
        <option value="true">Solo activos</option>
        <option value="false">Solo inactivos</option>
      </select>
    </>
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-800">Avisos</h2>
        {puede_gestionar && (
          <Link to="/avisos/nuevo">
            <Button>Nuevo aviso</Button>
          </Link>
        )}
      </div>

      <FilterableTable
        columns={columns}
        data={data ?? []}
        total={data?.length ?? 0}
        isLoading={isLoading}
        error={isError ? error?.message ?? "Error al cargar avisos" : null}
        filters={filter_bar}
        exportFileName="avisos.csv"
        pageSize={25}
      />

      <ConfirmDialog
        isOpen={!!deleteId}
        onConfirm={() => {
          if (deleteId) {
            eliminarAviso.mutate(deleteId);
            setDeleteId(null);
          }
        }}
        onCancel={() => setDeleteId(null)}
        title="Eliminar aviso"
        message="¿Estás seguro de que querés eliminar este aviso? Esta acción no se puede deshacer."
        variant="danger"
        confirmLabel="Eliminar"
      />
    </div>
  );
}
