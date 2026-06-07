import { api } from "@/shared/services/api";
import type { FechaAcademica, FechaAcademicaCreate, FechaAcademicaUpdate, FechaAcademicaFilters, FechasAcademicasResponse } from "@/features/fechas-academicas/types/fechas-academicas";

function build_params(filters?: FechaAcademicaFilters): Record<string, string> {
  const params: Record<string, string> = {};
  if (filters?.materia_id) params.materia_id = filters.materia_id;
  if (filters?.cohorte_id) params.cohorte_id = filters.cohorte_id;
  if (filters?.tipo) params.tipo = filters.tipo;
  if (filters?.periodo) params.periodo = filters.periodo;
  return params;
}

export async function fetchFechasAcademicas(filters?: FechaAcademicaFilters): Promise<FechasAcademicasResponse> {
  const { data } = await api.get<FechaAcademica[]>("/fechas-academicas", { params: build_params(filters) });
  return { items: data, total: data.length };
}

export async function crearFecha(input: FechaAcademicaCreate): Promise<FechaAcademica> {
  const { data } = await api.post<FechaAcademica>("/fechas-academicas", input);
  return data;
}

export async function actualizarFecha(id: string, input: FechaAcademicaUpdate): Promise<FechaAcademica> {
  const { data } = await api.patch<FechaAcademica>(`/fechas-academicas/${id}`, input);
  return data;
}

export async function eliminarFecha(id: string): Promise<void> {
  await api.delete(`/fechas-academicas/${id}`);
}

export async function exportarLMS(materiaId: string, cohorteId: string): Promise<Blob> {
  const { data } = await api.get("/fechas-academicas/lms-export", {
    params: { materia_id: materiaId, cohorte_id: cohorteId },
    responseType: "blob",
  });
  return data;
}
