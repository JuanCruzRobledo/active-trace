import { api } from "@/shared/services/api";
import type {
  AvisoCreate,
  AvisoUpdate,
  AvisoResponse,
  AvisoTimelineItem,
  TrackingAvisoResponse,
  AvisoFilters,
} from "@/features/avisos/types/avisos";

export async function fetchAvisos(filters?: AvisoFilters): Promise<AvisoResponse[]> {
  const { data } = await api.get<{items: AvisoResponse[], total: number}>("/avisos", { params: filters });
  return data.items;
}

export async function fetchAvisoTimeline(): Promise<AvisoTimelineItem[]> {
  const { data } = await api.get<AvisoTimelineItem[]>("/avisos/timeline");
  return data;
}

export async function fetchAvisoById(id: string): Promise<AvisoResponse> {
  const { data } = await api.get<AvisoResponse>(`/avisos/${id}`);
  return data;
}

export async function crearAviso(req: AvisoCreate): Promise<AvisoResponse> {
  const { data } = await api.post<AvisoResponse>("/avisos", req);
  return data;
}

export async function actualizarAviso(id: string, req: AvisoUpdate): Promise<AvisoResponse> {
  const { data } = await api.put<AvisoResponse>(`/avisos/${id}`, req);
  return data;
}

export async function eliminarAviso(id: string): Promise<void> {
  await api.delete(`/avisos/${id}`);
}

export async function acknowledgeAviso(id: string): Promise<void> {
  await api.post(`/avisos/${id}/acknowledge`);
}

export async function fetchTracking(id: string): Promise<TrackingAvisoResponse> {
  const { data } = await api.get<TrackingAvisoResponse>(`/avisos/${id}/tracking`);
  return data;
}
