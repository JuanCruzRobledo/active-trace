import { useQuery } from "@tanstack/react-query";
import { getMonitorGeneral } from "@/features/monitores/services/monitores";
import type {
  MonitorGeneralFilters,
  MonitorGeneralResponse,
} from "@/features/monitores/types/monitores";

export function useMonitorGeneral(filters?: MonitorGeneralFilters) {
  return useQuery<MonitorGeneralResponse>({
    queryKey: ["monitores-general", filters],
    queryFn: () => getMonitorGeneral(filters),
  });
}
