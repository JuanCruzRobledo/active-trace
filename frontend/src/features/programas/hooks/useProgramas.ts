import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchProgramas,
  subirPrograma,
  eliminarPrograma,
} from "@/features/programas/services/programas";
import type { ProgramaFilters } from "@/features/programas/types/programas";

const PROGRAMAS_QUERY_KEY = ["programas"] as const;

export function useProgramas(filters?: ProgramaFilters) {
  return useQuery({
    queryKey: [...PROGRAMAS_QUERY_KEY, filters],
    queryFn: () => fetchProgramas(filters),
  });
}

export function useSubirPrograma() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) => subirPrograma(formData),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PROGRAMAS_QUERY_KEY });
    },
  });
}

export function useEliminarPrograma() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => eliminarPrograma(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PROGRAMAS_QUERY_KEY });
    },
  });
}
