import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  useCohortes,
  useCrearCohorte,
  useActualizarCohorte,
} from "@/features/estructura-academica/hooks/useEstructura";
import {
  CohorteCreateSchema,
} from "@/features/estructura-academica/types/estructura";
import type {
  Cohorte,
  CohorteCreate,
} from "@/features/estructura-academica/types/estructura";
import { FilterableTable } from "@/shared/components/FilterableTable";
import type { Column } from "@/shared/components/FilterableTable";

function CohorteForm({
  defaultValues,
  onClose,
  onSubmit,
  isPending,
}: {
  defaultValues?: Partial<CohorteCreate>;
  onClose: () => void;
  onSubmit: (data: CohorteCreate) => void;
  isPending: boolean;
}) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CohorteCreate>({
    resolver: zodResolver(CohorteCreateSchema),
    defaultValues,
  });

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="space-y-4 rounded-lg border bg-gray-50 p-4"
    >
      <h3 className="font-semibold text-gray-800">
        {defaultValues ? "Editar cohorte" : "Nueva cohorte"}
      </h3>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label
            htmlFor="coh-nombre"
            className="block text-sm font-medium text-gray-700"
          >
            Nombre
          </label>
          <input
            id="coh-nombre"
            {...register("nombre")}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          {errors.nombre && (
            <p className="mt-1 text-xs text-red-600">{errors.nombre.message}</p>
          )}
        </div>

        <div>
          <label
            htmlFor="coh-anio"
            className="block text-sm font-medium text-gray-700"
          >
            Año
          </label>
          <input
            id="coh-anio"
            type="number"
            {...register("anio", { valueAsNumber: true })}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
            placeholder="2026"
          />
        </div>

        <div>
          <label
            htmlFor="coh-desde"
            className="block text-sm font-medium text-gray-700"
          >
            Vigencia desde
          </label>
          <input
            id="coh-desde"
            type="date"
            {...register("vig_desde")}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        <div>
          <label
            htmlFor="coh-hasta"
            className="block text-sm font-medium text-gray-700"
          >
            Vigencia hasta
          </label>
          <input
            id="coh-hasta"
            type="date"
            {...register("vig_hasta")}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
      </div>

      <div className="flex justify-end gap-3">
        <button
          type="button"
          onClick={onClose}
          className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={isPending}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {isPending ? "Guardando..." : "Guardar cohorte"}
        </button>
      </div>
    </form>
  );
}

export function CohortesPage() {
  const [showForm, setShowForm] = useState(false);
  const [editTarget, setEditTarget] = useState<Cohorte | null>(null);

  const { data: cohortes = [], isLoading, error } = useCohortes();
  const crearMutation = useCrearCohorte();
  const actualizarMutation = useActualizarCohorte();

  const rows = cohortes as unknown as Record<string, unknown>[];

  const columns: Column<Record<string, unknown>>[] = [
    { key: "nombre", label: "Nombre", sortable: true },
    { key: "anio", label: "Año", sortable: true },
    { key: "vig_desde", label: "Desde" },
    { key: "vig_hasta", label: "Hasta", render: (row) => (row.vig_hasta as string) ?? "—" },
    {
      key: "estado",
      label: "Estado",
      render: (row) =>
        row.estado !== "Inactiva" ? (
          <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-800">
            Activa
          </span>
        ) : (
          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
            Inactiva
          </span>
        ),
    },
    {
      key: "acciones",
      label: "Acciones",
      render: (row) => {
        const cohorte = row as unknown as Cohorte;
        return (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setEditTarget(cohorte)}
              className="text-xs text-brand-600 underline hover:text-brand-800"
            >
              Editar
            </button>
            <button
              type="button"
              onClick={() =>
                actualizarMutation.mutate({
                  id: cohorte.id,
                  payload: { estado: cohorte.estado === "Inactiva" ? "Activa" : "Inactiva" },
                })
              }
              className="text-xs text-gray-500 underline hover:text-gray-700"
            >
              {cohorte.estado === "Inactiva" ? "Activar" : "Desactivar"}
            </button>
          </div>
        );
      },
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Cohortes</h1>
          <p className="mt-1 text-sm text-gray-500">ABM de cohortes académicas</p>
        </div>
        <button
          type="button"
          onClick={() => {
            setEditTarget(null);
            setShowForm(true);
          }}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          Nueva cohorte
        </button>
      </div>

      {(showForm || editTarget) && (
        <CohorteForm
          defaultValues={
            editTarget
              ? {
                  nombre: editTarget.nombre,
                  anio: editTarget.anio ?? undefined,
                  vig_desde: editTarget.vig_desde ?? undefined,
                  vig_hasta: editTarget.vig_hasta ?? undefined,
                }
              : undefined
          }
          onClose={() => {
            setShowForm(false);
            setEditTarget(null);
          }}
          onSubmit={async (data) => {
            if (editTarget) {
              await actualizarMutation.mutateAsync({
                id: editTarget.id,
                payload: { nombre: data.nombre, vig_desde: data.vig_desde, vig_hasta: data.vig_hasta },
              });
            } else {
              await crearMutation.mutateAsync(data);
            }
            setShowForm(false);
            setEditTarget(null);
          }}
          isPending={crearMutation.isPending || actualizarMutation.isPending}
        />
      )}

      <FilterableTable
        columns={columns}
        data={rows}
        total={cohortes.length}
        isLoading={isLoading}
        error={error?.message ?? null}
        exportFileName="cohortes.csv"
      />
    </div>
  );
}
