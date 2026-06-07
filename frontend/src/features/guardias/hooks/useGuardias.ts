import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchGuardias,
  crearGuardia,
  actualizarGuardia,
} from "@/features/guardias/services/guardias";
import type { GuardiaFilters, GuardiaCreate, GuardiaUpdate } from "@/features/guardias/types/guardias";

const GUARDIAS_QUERY_KEY = ["guardias"] as const;

export function useGuardias(filters?: GuardiaFilters) {
  return useQuery({
    queryKey: [...GUARDIAS_QUERY_KEY, filters],
    queryFn: () => fetchGuardias(filters),
  });
}

export function useCrearGuardia() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: GuardiaCreate) => crearGuardia(input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: GUARDIAS_QUERY_KEY });
    },
  });
}

export function useActualizarGuardia() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: GuardiaUpdate }) => actualizarGuardia(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: GUARDIAS_QUERY_KEY });
    },
  });
}
