import { api } from "@/shared/services/api";

export interface RankingRow {
  alumno_id: string;
  alumno: string;
  legajo: string;
  actividades_aprobadas: number;
  total_actividades: number;
  porcentaje: number;
}

export interface NotaFinalRow {
  alumno_id: string;
  alumno: string;
  legajo: string;
  nota_final: number;
}

export interface RankingResponse {
  items: RankingRow[];
  total: number;
}

export interface NotasFinalesResponse {
  items: NotaFinalRow[];
  total: number;
}

export async function getRanking(materiaId: string): Promise<RankingResponse> {
  const { data } = await api.get<RankingResponse>(
    `/analisis/ranking`,
    { params: { materia_id: materiaId } },
  );
  return data;
}

export async function getNotasFinales(
  materiaId: string,
): Promise<NotasFinalesResponse> {
  const { data } = await api.get<NotasFinalesResponse>(
    `/analisis/notas-finales`,
    { params: { materia_id: materiaId } },
  );
  return data;
}
