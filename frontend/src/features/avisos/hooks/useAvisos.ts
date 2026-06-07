import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchAvisos,
  fetchAvisoTimeline,
  fetchAvisoById,
  crearAviso,
  actualizarAviso,
  eliminarAviso,
  acknowledgeAviso,
  fetchTracking,
} from "@/features/avisos/services/avisos";
import type { AvisoFilters } from "@/features/avisos/types/avisos";

export function useAvisos(filters?: AvisoFilters) {
  return useQuery({
    queryKey: ["avisos", filters],
    queryFn: () => fetchAvisos(filters),
  });
}

export function useAvisoTimeline() {
  return useQuery({
    queryKey: ["avisos", "timeline"],
    queryFn: fetchAvisoTimeline,
  });
}

export function useAvisoById(id: string) {
  return useQuery({
    queryKey: ["avisos", id],
    queryFn: () => fetchAvisoById(id),
    enabled: !!id,
  });
}

export function useCrearAviso() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: crearAviso,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["avisos"] });
      qc.invalidateQueries({ queryKey: ["avisos", "timeline"] });
    },
  });
}

export function useActualizarAviso() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof actualizarAviso>[1] }) =>
      actualizarAviso(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["avisos"] });
      qc.invalidateQueries({ queryKey: ["avisos", "timeline"] });
    },
  });
}

export function useEliminarAviso() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: eliminarAviso,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["avisos"] });
      qc.invalidateQueries({ queryKey: ["avisos", "timeline"] });
    },
  });
}

export function useAcknowledgeAviso() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: acknowledgeAviso,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["avisos"] });
      qc.invalidateQueries({ queryKey: ["avisos", "timeline"] });
    },
  });
}

export function useTracking(id: string) {
  return useQuery({
    queryKey: ["avisos", id, "tracking"],
    queryFn: () => fetchTracking(id),
    enabled: !!id,
  });
}
