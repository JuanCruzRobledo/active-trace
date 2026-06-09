import { api } from "@/shared/services/api";

export interface ReportesResponse {
  total_alumnos: number;
  actividades_registradas: number;
  porcentaje_aprobacion: number;
  alumnos_atrasados: number;
  alumnos_al_dia: number;
  tiene_datos: boolean;
}

export async function getReportes(
  materiaId: string,
): Promise<ReportesResponse> {
  const { data } = await api.get<ReportesResponse>(
    `/analisis/reporte-rapido`,
    { params: { materia_id: materiaId } },
  );
  return data;
}

export async function exportarEntregasSinCorregir(
  materiaId: string,
): Promise<Blob> {
  const { data } = await api.get<Blob>(
    `/analisis/tps-sin-corregir`,
    { params: { materia_id: materiaId }, responseType: "blob" },
  );
  return data;
}
