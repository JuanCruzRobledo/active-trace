import { useQuery } from "@tanstack/react-query";
import {
  fetchAccionesPorDia,
  fetchComunicacionesPorDocente,
  fetchInteraccionesPorDocenteMateria,
  fetchUltimasAcciones,
  fetchLog,
} from "@/features/auditoria/services/auditoria";
import type {
  AuditoriaFilters,
  LogFilters,
} from "@/features/auditoria/types/auditoria";

export function useAccionesPorDia(filters?: AuditoriaFilters) {
  return useQuery({
    queryKey: ["auditoria", "acciones-por-dia", filters],
    queryFn: () => fetchAccionesPorDia(filters),
  });
}

export function useComunicacionesPorDocente(filters?: AuditoriaFilters) {
  return useQuery({
    queryKey: ["auditoria", "comunicaciones-por-docente", filters],
    queryFn: () => fetchComunicacionesPorDocente(filters),
  });
}

export function useInteraccionesPorDocenteMateria(filters?: AuditoriaFilters) {
  return useQuery({
    queryKey: ["auditoria", "interacciones", filters],
    queryFn: () => fetchInteraccionesPorDocenteMateria(filters),
  });
}

export function useUltimasAcciones(limit?: number) {
  return useQuery({
    queryKey: ["auditoria", "ultimas-acciones", limit],
    queryFn: () => fetchUltimasAcciones(limit),
  });
}

export function useLog(filters?: LogFilters) {
  return useQuery({
    queryKey: ["auditoria", "log", filters],
    queryFn: () => fetchLog(filters),
  });
}
