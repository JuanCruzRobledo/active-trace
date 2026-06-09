import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchMisEquipos,
  fetchAsignaciones,
  asignacionMasiva,
  clonarEquipo,
  actualizarVigencia,
  exportarEquipo,
} from "@/features/equipos/services/equipos";
import type { EquipoFilters } from "@/features/equipos/types/equipos";

export function useMisEquipos(filters?: EquipoFilters) {
  return useQuery({
    queryKey: ["mis-equipos", filters],
    queryFn: () => fetchMisEquipos(filters),
  });
}

export function useAsignaciones(filters?: EquipoFilters) {
  return useQuery({
    queryKey: ["equipos", filters],
    queryFn: () => fetchAsignaciones(filters),
  });
}

export function useAsignacionMasiva() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: asignacionMasiva,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["equipos"] });
      qc.invalidateQueries({ queryKey: ["mis-equipos"] });
    },
  });
}

export function useClonarEquipo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: clonarEquipo,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["equipos"] });
      qc.invalidateQueries({ queryKey: ["mis-equipos"] });
    },
  });
}

export function useActualizarVigencia() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: actualizarVigencia,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["equipos"] });
      qc.invalidateQueries({ queryKey: ["mis-equipos"] });
    },
  });
}

export function useExportarEquipo() {
  return useMutation({
    mutationFn: ({
      materia_id,
      carrera_id,
      cohorte_id,
    }: {
      materia_id: string;
      carrera_id: string;
      cohorte_id: string;
    }) => exportarEquipo(materia_id, carrera_id, cohorte_id),
  });
}
