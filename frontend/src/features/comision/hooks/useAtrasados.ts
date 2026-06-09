import { useQuery } from "@tanstack/react-query";
import {
  getAtrasados,
  type AtrasadosResponse,
  type AtrasadosFilters,
} from "@/features/comision/services/atrasados";

export function useAtrasados(materiaId: string, filters?: AtrasadosFilters) {
  return useQuery<AtrasadosResponse>({
    queryKey: ["atrasados", materiaId, filters],
    queryFn: () => getAtrasados(materiaId, filters),
    enabled: !!materiaId,
  });
}
