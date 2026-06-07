import { api } from "@/shared/services/api";
import type {
  InstanciaListResponse,
  InstanciasFilters,
} from "@/features/encuentros/types/encuentros";

export async function fetchInstancias(
  filters?: InstanciasFilters,
): Promise<InstanciaListResponse> {
  const params: Record<string, string> = {};
  if (filters?.materia_id) params.materia_id = filters.materia_id;
  if (filters?.slot_id) params.slot_id = filters.slot_id;
  if (filters?.desde) params.desde = filters.desde;
  if (filters?.hasta) params.hasta = filters.hasta;
  if (filters?.estado) params.estado = filters.estado;
  const { data } = await api.get<InstanciaListResponse>("/encuentros/instancias", { params });
  return data;
}
