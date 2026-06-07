import { api } from "@/shared/services/api";
import type {
  MonitorGeneralFilters,
  MonitorGeneralResponse,
} from "@/features/monitores/types/monitores";

export async function getMonitorGeneral(
  filters?: MonitorGeneralFilters,
): Promise<MonitorGeneralResponse> {
  const params: Record<string, string> = {};
  if (filters?.materia_id) params.materia_id = filters.materia_id;
  if (filters?.regional) params.regional = filters.regional;
  if (filters?.comision) params.comision = filters.comision;
  if (filters?.q) params.q = filters.q;
  const { data } = await api.get<MonitorGeneralResponse>(
    "/analisis/monitor-general",
    { params },
  );
  return data;
}
