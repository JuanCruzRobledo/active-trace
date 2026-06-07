import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchMisTareas,
  fetchTareasAdmin,
  fetchTareaById,
  crearTarea,
  actualizarEstadoTarea,
  agregarComentario,
} from "@/features/tareas/services/tareas";
import type {
  TareaCreate,
  TareaEstadoUpdate,
  ComentarioCreate,
  TareasFilters,
} from "@/features/tareas/types/tareas";

export function useMisTareas(estado?: string, materiaId?: string) {
  return useQuery({
    queryKey: ["tareas", "mias", { estado, materiaId }],
    queryFn: () => fetchMisTareas(estado, materiaId),
  });
}

export function useTareasAdmin(filters?: TareasFilters) {
  return useQuery({
    queryKey: ["tareas", "admin", filters],
    queryFn: () => fetchTareasAdmin(filters),
  });
}

export function useTareaById(id: string | undefined) {
  return useQuery({
    queryKey: ["tareas", id],
    queryFn: () => fetchTareaById(id!),
    enabled: !!id,
  });
}

export function useCrearTarea() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: TareaCreate) => crearTarea(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tareas"] });
    },
  });
}

export function useActualizarEstadoTarea() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: TareaEstadoUpdate }) =>
      actualizarEstadoTarea(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tareas"] });
    },
  });
}

export function useAgregarComentario() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      tareaId,
      payload,
    }: {
      tareaId: string;
      payload: ComentarioCreate;
    }) => agregarComentario(tareaId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tareas"] });
    },
  });
}
