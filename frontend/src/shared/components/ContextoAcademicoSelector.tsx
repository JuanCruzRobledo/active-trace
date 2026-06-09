import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/services/api";
import { LoadingSpinner } from "./LoadingSpinner";

interface ContextoAcademico {
  carreraId: string;
  cohorteId: string;
  materiaId: string;
}

interface ContextoAcademicoSelectorProps {
  onChange: (context: ContextoAcademico) => void;
  initialValues?: Partial<ContextoAcademico>;
}

interface CarreraOption {
  id: string;
  nombre: string;
}

interface CohorteOption {
  id: string;
  nombre: string;
}

interface MateriaOption {
  id: string;
  nombre: string;
}

async function fetchCarreras(): Promise<CarreraOption[]> {
  const { data } = await api.get<CarreraOption[]>("/admin/carreras");
  return data;
}

async function fetchCohortes(carreraId: string): Promise<CohorteOption[]> {
  const { data } = await api.get<(CohorteOption & { carrera_id: string })[]>("/admin/cohortes");
  return data.filter((c) => c.carrera_id === carreraId);
}

async function fetchMaterias(): Promise<MateriaOption[]> {
  const { data } = await api.get<MateriaOption[]>("/admin/materias");
  return data;
}

export function ContextoAcademicoSelector({
  onChange,
  initialValues,
}: ContextoAcademicoSelectorProps) {
  const [carreraId, setCarreraId] = useState(initialValues?.carreraId ?? "");
  const [cohorteId, setCohorteId] = useState(initialValues?.cohorteId ?? "");
  const [materiaId, setMateriaId] = useState(initialValues?.materiaId ?? "");

  const carrerasQuery = useQuery({
    queryKey: ["carreras"],
    queryFn: fetchCarreras,
  });

  const cohortesQuery = useQuery({
    queryKey: ["cohortes", carreraId],
    queryFn: () => fetchCohortes(carreraId),
    enabled: !!carreraId,
  });

  const materiasQuery = useQuery({
    queryKey: ["materias"],
    queryFn: fetchMaterias,
    enabled: !!cohorteId,
  });

  useEffect(() => {
    if (carreraId && cohorteId && materiaId) {
      onChange({ carreraId, cohorteId, materiaId });
    }
  }, [carreraId, cohorteId, materiaId, onChange]);

  const handleCarreraChange = (value: string) => {
    setCarreraId(value);
    setCohorteId("");
    setMateriaId("");
  };

  const handleCohorteChange = (value: string) => {
    setCohorteId(value);
    setMateriaId("");
  };

  const selectClass =
    "block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm transition-colors focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-1 disabled:cursor-not-allowed disabled:bg-gray-100 disabled:text-gray-500";

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      {/* Carrera */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Carrera
        </label>
        {carrerasQuery.isLoading ? (
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <LoadingSpinner size="h-4 w-4" /> Cargando...
          </div>
        ) : carrerasQuery.isError ? (
          <p className="text-sm text-red-600">Error al cargar carreras</p>
        ) : (
          <select
            value={carreraId}
            onChange={(e) => handleCarreraChange(e.target.value)}
            className={selectClass}
          >
            <option value="">Seleccionar carrera</option>
            {(carrerasQuery.data ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Cohorte */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Cohorte
        </label>
        {!carreraId ? (
          <p className="text-sm text-gray-400">Seleccioná una carrera primero</p>
        ) : cohortesQuery.isLoading ? (
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <LoadingSpinner size="h-4 w-4" /> Cargando...
          </div>
        ) : cohortesQuery.isError ? (
          <p className="text-sm text-red-600">Error al cargar cohortes</p>
        ) : (
          <select
            value={cohorteId}
            onChange={(e) => handleCohorteChange(e.target.value)}
            className={selectClass}
            disabled={!carreraId}
          >
            <option value="">Seleccionar cohorte</option>
            {(cohortesQuery.data ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Materia */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Materia
        </label>
        {!cohorteId ? (
          <p className="text-sm text-gray-400">Seleccioná un cohorte primero</p>
        ) : materiasQuery.isLoading ? (
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <LoadingSpinner size="h-4 w-4" /> Cargando...
          </div>
        ) : materiasQuery.isError ? (
          <p className="text-sm text-red-600">Error al cargar materias</p>
        ) : (
          <select
            value={materiaId}
            onChange={(e) => setMateriaId(e.target.value)}
            className={selectClass}
            disabled={!cohorteId}
          >
            <option value="">Seleccionar materia</option>
            {(materiasQuery.data ?? []).map((m) => (
              <option key={m.id} value={m.id}>
                {m.nombre}
              </option>
            ))}
          </select>
        )}
      </div>
    </div>
  );
}
