import { api } from "@/shared/services/api";
import type { Guardia, GuardiaCreate, GuardiaUpdate, GuardiaFilters, GuardiasResponse } from "@/features/guardias/types/guardias";

function build_params(filters?: GuardiaFilters): Record<string, string> {
  const params: Record<string, string> = {};
  if (filters?.materia_id) params.materia_id = filters.materia_id;
  if (filters?.usuario_id) params.usuario_id = filters.usuario_id;
  if (filters?.desde) params.desde = filters.desde;
  if (filters?.hasta) params.hasta = filters.hasta;
  if (filters?.estado) params.estado = filters.estado;
  return params;
}

export async function fetchGuardias(filters?: GuardiaFilters): Promise<GuardiasResponse> {
  const { data } = await api.get<GuardiasResponse>("/guardias", { params: build_params(filters) });
  return data;
}

export async function crearGuardia(input: GuardiaCreate): Promise<Guardia> {
  const { data } = await api.post<Guardia>("/guardias", input);
  return data;
}

export async function actualizarGuardia(id: string, input: GuardiaUpdate): Promise<Guardia> {
  const { data } = await api.patch<Guardia>(`/guardias/${id}`, input);
  return data;
}

export async function exportarGuardias(filters?: GuardiaFilters): Promise<Blob> {
  const { data } = await api.get("/guardias/exportar", {
    params: build_params(filters),
    responseType: "blob",
  });
  return data;
}
