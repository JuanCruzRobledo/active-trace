import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getUmbral,
  updateUmbral,
  type UmbralResponse,
  type UmbralMateriaResponse,
} from "@/features/comision/services/umbral";

export function useUmbralMateria(materiaId: string, asignacionId: string) {
  return useQuery<UmbralResponse>({
    queryKey: ["umbral", materiaId, asignacionId],
    queryFn: () => getUmbral(materiaId, asignacionId),
    enabled: !!materiaId && !!asignacionId,
  });
}

export function useUpdateUmbral(materiaId: string, asignacionId: string) {
  const queryClient = useQueryClient();
  return useMutation<UmbralMateriaResponse, Error, number>({
    mutationFn: (porcentaje: number) =>
      updateUmbral(materiaId, asignacionId, porcentaje),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["umbral", materiaId, asignacionId],
      });
    },
  });
}
