import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  useSalariosBase,
  useSalariosPlus,
  useClavesPlusByActive,
  useCrearSalarioBase,
  useCrearSalarioPlus,
  useCrearClavePlus,
} from "@/features/liquidaciones/hooks/useLiquidaciones";
import {
  SalarioBaseCreateSchema,
  SalarioPlusCreateSchema,
  ClavePlusCreateSchema,
} from "@/features/liquidaciones/types/liquidaciones";
import type {
  SalarioBaseCreate,
  SalarioPlusCreate,
  ClavePlusCreate,
} from "@/features/liquidaciones/types/liquidaciones";
import { FilterableTable } from "@/shared/components/FilterableTable";
import type { Column } from "@/shared/components/FilterableTable";

// ─── Salarios Base Form ───────────────────────────────────────────────────────

function SalarioBaseForm({ onClose }: { onClose: () => void }) {
  const { mutateAsync, isPending } = useCrearSalarioBase();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SalarioBaseCreate>({
    resolver: zodResolver(SalarioBaseCreateSchema),
  });

  async function onSubmit(data: SalarioBaseCreate) {
    await mutateAsync(data);
    onClose();
  }

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="space-y-4 rounded-lg border bg-gray-50 p-4"
    >
      <h3 className="font-semibold text-gray-800">Nuevo salario base</h3>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label
            htmlFor="sb-rol"
            className="block text-sm font-medium text-gray-700"
          >
            Rol
          </label>
          <input
            id="sb-rol"
            {...register("rol")}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
            placeholder="TUTOR"
          />
          {errors.rol && (
            <p className="mt-1 text-xs text-red-600">{errors.rol.message}</p>
          )}
        </div>

        <div>
          <label
            htmlFor="sb-monto"
            className="block text-sm font-medium text-gray-700"
          >
            Monto
          </label>
          <input
            id="sb-monto"
            {...register("monto")}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
            placeholder="10000.00"
          />
          {errors.monto && (
            <p className="mt-1 text-xs text-red-600">{errors.monto.message}</p>
          )}
        </div>

        <div>
          <label
            htmlFor="sb-desde"
            className="block text-sm font-medium text-gray-700"
          >
            Vigente desde
          </label>
          <input
            id="sb-desde"
            type="date"
            {...register("desde")}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        <div>
          <label
            htmlFor="sb-hasta"
            className="block text-sm font-medium text-gray-700"
          >
            Vigente hasta
          </label>
          <input
            id="sb-hasta"
            type="date"
            {...register("hasta")}
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
          {isPending ? "Guardando..." : "Guardar salario base"}
        </button>
      </div>
    </form>
  );
}

// ─── Salarios Plus Form ───────────────────────────────────────────────────────

function SalarioPlusForm({ onClose }: { onClose: () => void }) {
  const { mutateAsync, isPending } = useCrearSalarioPlus();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SalarioPlusCreate>({
    resolver: zodResolver(SalarioPlusCreateSchema),
  });

  async function onSubmit(data: SalarioPlusCreate) {
    await mutateAsync(data);
    onClose();
  }

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="space-y-4 rounded-lg border bg-gray-50 p-4"
    >
      <h3 className="font-semibold text-gray-800">Nuevo salario plus</h3>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label
            htmlFor="sp-grupo"
            className="block text-sm font-medium text-gray-700"
          >
            Grupo
          </label>
          <input
            id="sp-grupo"
            {...register("grupo")}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
            placeholder="ANTIGUEDAD"
          />
          {errors.grupo && (
            <p className="mt-1 text-xs text-red-600">{errors.grupo.message}</p>
          )}
        </div>

        <div>
          <label
            htmlFor="sp-rol"
            className="block text-sm font-medium text-gray-700"
          >
            Rol
          </label>
          <input
            id="sp-rol"
            {...register("rol")}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
            placeholder="TUTOR"
          />
          {errors.rol && (
            <p className="mt-1 text-xs text-red-600">{errors.rol.message}</p>
          )}
        </div>

        <div className="sm:col-span-2">
          <label
            htmlFor="sp-desc"
            className="block text-sm font-medium text-gray-700"
          >
            Descripción
          </label>
          <input
            id="sp-desc"
            {...register("descripcion")}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          {errors.descripcion && (
            <p className="mt-1 text-xs text-red-600">
              {errors.descripcion.message}
            </p>
          )}
        </div>

        <div>
          <label
            htmlFor="sp-monto"
            className="block text-sm font-medium text-gray-700"
          >
            Monto
          </label>
          <input
            id="sp-monto"
            {...register("monto")}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          {errors.monto && (
            <p className="mt-1 text-xs text-red-600">{errors.monto.message}</p>
          )}
        </div>

        <div>
          <label
            htmlFor="sp-desde"
            className="block text-sm font-medium text-gray-700"
          >
            Vigente desde
          </label>
          <input
            id="sp-desde"
            type="date"
            {...register("desde")}
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
          {isPending ? "Guardando..." : "Guardar plus"}
        </button>
      </div>
    </form>
  );
}

// ─── Clave Plus Form ──────────────────────────────────────────────────────────

function ClavePlusForm({ onClose }: { onClose: () => void }) {
  const { mutateAsync, isPending } = useCrearClavePlus();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ClavePlusCreate>({
    resolver: zodResolver(ClavePlusCreateSchema),
  });

  async function onSubmit(data: ClavePlusCreate) {
    await mutateAsync(data);
    onClose();
  }

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="space-y-4 rounded-lg border bg-gray-50 p-4"
    >
      <h3 className="font-semibold text-gray-800">Nueva clave plus</h3>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label
            htmlFor="cp-codigo"
            className="block text-sm font-medium text-gray-700"
          >
            Código
          </label>
          <input
            id="cp-codigo"
            {...register("codigo")}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          {errors.codigo && (
            <p className="mt-1 text-xs text-red-600">{errors.codigo.message}</p>
          )}
        </div>

        <div>
          <label
            htmlFor="cp-nombre"
            className="block text-sm font-medium text-gray-700"
          >
            Nombre
          </label>
          <input
            id="cp-nombre"
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
          {isPending ? "Guardando..." : "Guardar clave"}
        </button>
      </div>
    </form>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

type ActiveForm = "base" | "plus" | "clave" | null;

export function GrillaSalarialPage() {
  const [activeForm, setActiveForm] = useState<ActiveForm>(null);

  const { data: salariosBase = [], isLoading: loadingBase, error: errorBase } =
    useSalariosBase();
  const { data: salariosPlus = [], isLoading: loadingPlus, error: errorPlus } =
    useSalariosPlus();
  const { data: clavesPlus = [], isLoading: loadingClaves, error: errorClaves } =
    useClavesPlusByActive();

  const baseRows = salariosBase as unknown as Record<string, unknown>[];
  const plusRows = salariosPlus as unknown as Record<string, unknown>[];
  const clavesRows = clavesPlus as unknown as Record<string, unknown>[];

  const baseColumns: Column<Record<string, unknown>>[] = [
    { key: "rol", label: "Rol", sortable: true },
    {
      key: "monto",
      label: "Monto",
      sortable: true,
      render: (row) => `$${row.monto as string}`,
    },
    { key: "desde", label: "Desde", sortable: true },
    { key: "hasta", label: "Hasta", render: (row) => (row.hasta as string) ?? "—" },
  ];

  const plusColumns: Column<Record<string, unknown>>[] = [
    { key: "grupo", label: "Grupo", sortable: true },
    { key: "rol", label: "Rol", sortable: true },
    { key: "descripcion", label: "Descripción" },
    {
      key: "monto",
      label: "Monto",
      sortable: true,
      render: (row) => `$${row.monto as string}`,
    },
    { key: "desde", label: "Desde" },
    { key: "hasta", label: "Hasta", render: (row) => (row.hasta as string) ?? "—" },
  ];

  const clavesColumns: Column<Record<string, unknown>>[] = [
    { key: "codigo", label: "Código", sortable: true },
    { key: "nombre", label: "Nombre", sortable: true },
    {
      key: "activa",
      label: "Activa",
      render: (row) =>
        row.activa ? (
          <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-800">
            Activa
          </span>
        ) : (
          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
            Inactiva
          </span>
        ),
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Grilla Salarial</h1>
        <p className="mt-1 text-sm text-gray-500">
          Gestión de salarios base, plus y claves plus
        </p>
      </div>

      {/* Salarios Base */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">Salarios Base</h2>
          <button
            type="button"
            onClick={() =>
              setActiveForm((prev) => (prev === "base" ? null : "base"))
            }
            className="inline-flex items-center gap-1 rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            Agregar
          </button>
        </div>

        {activeForm === "base" && (
          <SalarioBaseForm onClose={() => setActiveForm(null)} />
        )}

        <FilterableTable
          columns={baseColumns}
          data={baseRows}
          total={salariosBase.length}
          isLoading={loadingBase}
          error={errorBase?.message ?? null}
          exportFileName="salarios-base.csv"
        />
      </section>

      {/* Salarios Plus */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">Salarios Plus</h2>
          <button
            type="button"
            onClick={() =>
              setActiveForm((prev) => (prev === "plus" ? null : "plus"))
            }
            className="inline-flex items-center gap-1 rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            Agregar
          </button>
        </div>

        {activeForm === "plus" && (
          <SalarioPlusForm onClose={() => setActiveForm(null)} />
        )}

        <FilterableTable
          columns={plusColumns}
          data={plusRows}
          total={salariosPlus.length}
          isLoading={loadingPlus}
          error={errorPlus?.message ?? null}
          exportFileName="salarios-plus.csv"
        />
      </section>

      {/* Claves Plus */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">Claves Plus</h2>
          <button
            type="button"
            onClick={() =>
              setActiveForm((prev) => (prev === "clave" ? null : "clave"))
            }
            className="inline-flex items-center gap-1 rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            Agregar
          </button>
        </div>

        {activeForm === "clave" && (
          <ClavePlusForm onClose={() => setActiveForm(null)} />
        )}

        <FilterableTable
          columns={clavesColumns}
          data={clavesRows}
          total={clavesPlus.length}
          isLoading={loadingClaves}
          error={errorClaves?.message ?? null}
          exportFileName="claves-plus.csv"
        />
      </section>
    </div>
  );
}
