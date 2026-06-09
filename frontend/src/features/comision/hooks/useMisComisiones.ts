import { useQuery } from "@tanstack/react-query";
import { api } from "@/shared/services/api";

export interface EquipoItem {
  id: string;
  materia_id: string | null;
  materia_nombre: string | null;
  comisiones: string[] | null;
  rol: string;
}

export interface MisComisionesResult {
  comisiones: Array<{
    id: string;
    nombre: string;
    comision: string;
    asignacion_id: string;
  }>;
  isLoading: boolean;
  error: Error | null;
}

async function fetchMisEquipos(): Promise<EquipoItem[]> {
  const { data } = await api.get<EquipoItem[]>("/equipos/mis-equipos");
  return data;
}

export function useMisComisiones(): MisComisionesResult {
  const { data, isLoading, error } = useQuery<EquipoItem[], Error>({
    queryKey: ["mis-equipos"],
    queryFn: fetchMisEquipos,
  });

  const comisiones =
    data?.flatMap((eq) => {
      const materiaId = eq.materia_id;
      if (!materiaId) return [];
      const coms = eq.comisiones?.length ? eq.comisiones : ["General"];
      return coms.map((comision) => ({
        id: materiaId,
        nombre: eq.materia_nombre ?? "Sin nombre",
        comision,
        asignacion_id: eq.id,
      }));
    }) ?? [];

  return { comisiones, isLoading, error };
}
