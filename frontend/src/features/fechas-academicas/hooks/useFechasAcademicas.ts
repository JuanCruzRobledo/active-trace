import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchFechasAcademicas,
  crearFecha,
  actualizarFecha,
  eliminarFecha,
} from "@/features/fechas-academicas/services/fechas-academicas";
import type { FechaAcademicaCreate, FechaAcademicaUpdate, FechaAcademicaFilters } from "@/features/fechas-academicas/types/fechas-academicas";

const FECHAS_QUERY_KEY = ["fechas-academicas"] as const;

export function useFechasAcademicas(filters?: FechaAcademicaFilters) {
  return useQuery({
    queryKey: [...FECHAS_QUERY_KEY, filters],
    queryFn: () => fetchFechasAcademicas(filters),
  });
}

export function useCrearFecha() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: FechaAcademicaCreate) => crearFecha(input),
    onSuccess: () => { qc.invalidateQueries({ queryKey: FECHAS_QUERY_KEY }); },
  });
}

export function useActualizarFecha() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: FechaAcademicaUpdate }) => actualizarFecha(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: FECHAS_QUERY_KEY }); },
  });
}

export function useEliminarFecha() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => eliminarFecha(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: FECHAS_QUERY_KEY }); },
  });
}
