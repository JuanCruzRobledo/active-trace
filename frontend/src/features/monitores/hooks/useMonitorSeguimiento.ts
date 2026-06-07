import { useQuery } from "@tanstack/react-query";
import {
  getMonitores,
  type MonitoresResponse,
  type MonitoresFilters,
} from "@/features/monitores/services/seguimiento";

export function useMonitorSeguimiento(filters?: MonitoresFilters) {
  return useQuery<MonitoresResponse>({
    queryKey: ["monitores-seguimiento", filters],
    queryFn: () => getMonitores(filters),
  });
}
