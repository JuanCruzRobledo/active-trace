import { useQuery } from "@tanstack/react-query";
import {
  getReportes,
  type ReportesResponse,
} from "@/features/comision/services/reportes";

export function useReportes(materiaId: string) {
  return useQuery<ReportesResponse>({
    queryKey: ["reportes", materiaId],
    queryFn: () => getReportes(materiaId),
    enabled: !!materiaId,
  });
}
