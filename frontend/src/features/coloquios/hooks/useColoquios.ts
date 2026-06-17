import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchMetricas,
  fetchConvocatorias,
  fetchConvocatoriaById,
  crearConvocatoria,
  actualizarConvocatoria,
  cerrarConvocatoria,
  importarAlumnos,
  fetchAgenda,
} from "@/features/coloquios/services/coloquios";
import type {
  EvaluacionCreate,
  EvaluacionUpdate,
  ImportarAlumnosRequest,
  ConvocatoriasFilters,
} from "@/features/coloquios/types/coloquios";

export function useMetricas() {
  return useQuery({
    queryKey: ["coloquios", "metricas"],
    queryFn: fetchMetricas,
  });
}

export function useConvocatorias(filters?: ConvocatoriasFilters) {
  return useQuery({
    queryKey: ["coloquios", "convocatorias", filters],
    queryFn: () => fetchConvocatorias(filters),
  });
}

export function useCrearConvocatoria() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: EvaluacionCreate) => crearConvocatoria(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["coloquios"] });
    },
  });
}

export function useConvocatoriaById(id: string | undefined) {
  return useQuery({
    queryKey: ["coloquios", "convocatorias", id],
    queryFn: () => fetchConvocatoriaById(id!),
    enabled: !!id,
  });
}

export function useActualizarConvocatoria() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: EvaluacionUpdate }) =>
      actualizarConvocatoria(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["coloquios"] });
    },
  });
}

export function useCerrarConvocatoria() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (evaluacionId: string) => cerrarConvocatoria(evaluacionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["coloquios"] });
    },
  });
}

export function useImportarAlumnos() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      evaluacionId,
      payload,
    }: {
      evaluacionId: string;
      payload: ImportarAlumnosRequest;
    }) => importarAlumnos(evaluacionId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["coloquios"] });
    },
  });
}

export function useAgenda(evaluacionId?: string) {
  return useQuery({
    queryKey: ["coloquios", "agenda", evaluacionId],
    queryFn: () => fetchAgenda(evaluacionId),
  });
}
