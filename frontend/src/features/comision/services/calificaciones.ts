import { api } from "@/shared/services/api";

export interface PreviewRow {
  alumno: string;
  legajo: string;
  actividad: string;
  nota: number;
}

export interface PreviewResponse {
  filas: PreviewRow[];
  actividades: string[];
  total_filas: number;
  preview_token: string;
}

export interface ImportResult {
  importadas: number;
  errores: number;
  detalle_errores?: string[];
}

export async function previewCalificaciones(
  materiaId: string,
  file: File,
): Promise<PreviewResponse> {
  const form = new FormData();
  form.append("archivo", file);
  form.append("materia_id", materiaId);
  const { data } = await api.post<PreviewResponse>(
    `/calificaciones/importar/preview`,
    form,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return data;
}

export async function importarCalificaciones(
  materiaId: string,
  previewToken: string,
  actividades: string[],
): Promise<ImportResult> {
  const form = new FormData();
  form.append("preview_token", previewToken);
  form.append("materia_id", materiaId);
  form.append("actividades_seleccionadas", JSON.stringify(actividades));
  const { data } = await api.post<ImportResult>(
    `/calificaciones/importar/confirm`,
    form,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return data;
}
