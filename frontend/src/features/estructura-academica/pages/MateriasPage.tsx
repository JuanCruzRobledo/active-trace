import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  useMaterias,
  useCrearMateria,
  useActualizarMateria,
} from "@/features/estructura-academica/hooks/useEstructura";
import {
  MateriaCreateSchema,
} from "@/features/estructura-academica/types/estructura";
import type {
  Materia,
  MateriaCreate,
} from "@/features/estructura-academica/types/estructura";
import { FilterableTable } from "@/shared/components/FilterableTable";
import type { Column } from "@/shared/components/FilterableTable";

function MateriaForm({
  defaultValues,
  onClose,
  onSubmit,
  isPending,
}: {
  defaultValues?: Partial<MateriaCreate>;
  onClose: () => void;
  onSubmit: (data: MateriaCreate) => void;
  isPending: boolean;
}) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<MateriaCreate>({
    resolver: zodResolver(MateriaCreateSchema),
    defaultValues,
  });

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="space-y-4 rounded-lg border bg-gray-50 p-4"
    >
      <h3 className="font-semibold text-gray-800">
        {defaultValues ? "Editar materia" : "Nueva materia"}
      </h3>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label
            htmlFor="mat-codigo"
            className="block text-sm font-medium text-gray-700"
          >
            Código
          </label>
          <input
            id="mat-codigo"
            {...register("codigo")}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          {errors.codigo && (
            <p className="mt-1 text-xs text-red-600">{errors.codigo.message}</p>
          )}
        </div>

        <div>
          <label
            htmlFor="mat-nombre"
            className="block text-sm font-medium text-gray-700"
          >
            Nombre
          </label>
          <input
            id="mat-nombre"
            {...register("nombre")}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          {errors.nombre && (
            <p className="mt-1 text-xs text-red-600">{errors.nombre.message}</p>
          )}
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
          {isPending ? "Guardando..." : "Guardar materia"}
        </button>
      </div>
    </form>
  );
}

export function MateriasPage() {
  const [showForm, setShowForm] = useState(false);
  const [editTarget, setEditTarget] = useState<Materia | null>(null);

  const { data: materias = [], isLoading, error } = useMaterias();
  const crearMutation = useCrearMateria();
  const actualizarMutation = useActualizarMateria();

  const rows = materias as unknown as Record<string, unknown>[];

  const columns: Column<Record<string, unknown>>[] = [
    { key: "codigo", label: "Código", sortable: true },
    { key: "nombre", label: "Nombre", sortable: true },
    {
      key: "activa",
      label: "Estado",
      render: (row) =>
        row.activa !== false ? (
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
        const materia = row as unknown as Materia;
        return (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setEditTarget(materia)}
              className="text-xs text-brand-600 underline hover:text-brand-800"
            >
              Editar
            </button>
            <button
              type="button"
              onClick={() =>
                actualizarMutation.mutate({
                  id: materia.id,
                  payload: { activa: materia.activa === false },
                })
              }
              className="text-xs text-gray-500 underline hover:text-gray-700"
            >
              {materia.activa === false ? "Activar" : "Desactivar"}
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
          <h1 className="text-2xl font-bold text-gray-900">Materias</h1>
          <p className="mt-1 text-sm text-gray-500">ABM de materias</p>
        </div>
        <button
          type="button"
          onClick={() => {
            setEditTarget(null);
            setShowForm(true);
          }}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          Nueva materia
        </button>
      </div>

      {(showForm || editTarget) && (
        <MateriaForm
          defaultValues={
            editTarget
              ? { codigo: editTarget.codigo, nombre: editTarget.nombre }
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
                payload: data,
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
        total={materias.length}
        isLoading={isLoading}
        error={error?.message ?? null}
        exportFileName="materias.csv"
      />
    </div>
  );
}
