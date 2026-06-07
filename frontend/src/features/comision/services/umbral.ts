import { api } from "@/shared/services/api";

export interface UmbralResponse {
  umbral_pct: number;
  materia_id: string;
  asignacion_id?: string;
}

export interface UmbralMateriaResponse {
  id: string;
  materia_id: string;
  asignacion_id: string;
  umbral_pct: number;
  valores_aprobatorios?: Record<string, number>;
  calificaciones_recalculadas: number;
}

export async function getUmbral(
  materiaId: string,
  asignacionId: string,
): Promise<UmbralResponse> {
  const { data } = await api.get<UmbralResponse>(
    `/calificaciones/umbral`,
    { params: { materia_id: materiaId, asignacion_id: asignacionId } },
  );
  return data;
}

export async function updateUmbral(
  materiaId: string,
  asignacionId: string,
  umbralPct: number,
): Promise<UmbralMateriaResponse> {
  const { data } = await api.put<UmbralMateriaResponse>(
    `/calificaciones/umbral`,
    { materia_id: materiaId, asignacion_id: asignacionId, umbral_pct: umbralPct },
  );
  return data;
}
