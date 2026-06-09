import { api } from "@/shared/services/api";
import type { Programa, ProgramaFilters, ProgramasResponse } from "@/features/programas/types/programas";

export async function fetchProgramas(filters?: ProgramaFilters): Promise<ProgramasResponse> {
  const params: Record<string, string> = {};
  if (filters?.materia_id) params.materia_id = filters.materia_id;
  if (filters?.carrera_id) params.carrera_id = filters.carrera_id;
  if (filters?.cohorte_id) params.cohorte_id = filters.cohorte_id;
  const { data } = await api.get<Programa[]>("/programas", { params });
  return { items: data, total: data.length };
}

export async function subirPrograma(formData: FormData): Promise<Programa> {
  const { data } = await api.post<Programa>("/programas", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function eliminarPrograma(id: string): Promise<void> {
  await api.delete(`/programas/${id}`);
}
