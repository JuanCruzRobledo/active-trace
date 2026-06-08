import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchCarreras,
  fetchCarreraById,
  crearCarrera,
  actualizarCarrera,
  fetchCohortes,
  fetchCohorteById,
  crearCohorte,
  actualizarCohorte,
  fetchMaterias,
  fetchMateriaById,
  crearMateria,
  actualizarMateria,
} from "@/features/estructura-academica/services/estructura";
import type {
  CarreraCreate,
  CarreraUpdate,
  CohorteCreate,
  CohorteUpdate,
  MateriaCreate,
  MateriaUpdate,
} from "@/features/estructura-academica/types/estructura";

// ─── Carreras ─────────────────────────────────────────────────────────────────

export function useCarreras() {
  return useQuery({
    queryKey: ["carreras"],
    queryFn: fetchCarreras,
  });
}

export function useCarreraById(id: string | undefined) {
  return useQuery({
    queryKey: ["carreras", id],
    queryFn: () => fetchCarreraById(id!),
    enabled: !!id,
  });
}

export function useCrearCarrera() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CarreraCreate) => crearCarrera(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["carreras"] });
    },
  });
}

export function useActualizarCarrera() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: CarreraUpdate }) =>
      actualizarCarrera(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["carreras"] });
    },
  });
}

// ─── Cohortes ─────────────────────────────────────────────────────────────────

export function useCohortes() {
  return useQuery({
    queryKey: ["cohortes"],
    queryFn: fetchCohortes,
  });
}

export function useCohorteById(id: string | undefined) {
  return useQuery({
    queryKey: ["cohortes", id],
    queryFn: () => fetchCohorteById(id!),
    enabled: !!id,
  });
}

export function useCrearCohorte() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CohorteCreate) => crearCohorte(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cohortes"] });
    },
  });
}

export function useActualizarCohorte() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: CohorteUpdate }) =>
      actualizarCohorte(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cohortes"] });
    },
  });
}

// ─── Materias ─────────────────────────────────────────────────────────────────

export function useMaterias() {
  return useQuery({
    queryKey: ["materias-admin"],
    queryFn: fetchMaterias,
  });
}

export function useMateriaById(id: string | undefined) {
  return useQuery({
    queryKey: ["materias-admin", id],
    queryFn: () => fetchMateriaById(id!),
    enabled: !!id,
  });
}

export function useCrearMateria() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: MateriaCreate) => crearMateria(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["materias-admin"] });
    },
  });
}

export function useActualizarMateria() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: MateriaUpdate }) =>
      actualizarMateria(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["materias-admin"] });
    },
  });
}
