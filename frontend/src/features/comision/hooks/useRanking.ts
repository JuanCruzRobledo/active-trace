import { useQuery } from "@tanstack/react-query";
import {
  getRanking,
  getNotasFinales,
  type RankingResponse,
  type NotasFinalesResponse,
} from "@/features/comision/services/rankings";

export function useRanking(materiaId: string) {
  return useQuery<RankingResponse>({
    queryKey: ["ranking", materiaId],
    queryFn: () => getRanking(materiaId),
    enabled: !!materiaId,
  });
}

export function useNotasFinales(materiaId: string) {
  return useQuery<NotasFinalesResponse>({
    queryKey: ["notas-finales", materiaId],
    queryFn: () => getNotasFinales(materiaId),
    enabled: !!materiaId,
  });
}
