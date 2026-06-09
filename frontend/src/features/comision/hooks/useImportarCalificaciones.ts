import { useMutation } from "@tanstack/react-query";
import {
  previewCalificaciones,
  importarCalificaciones,
  type PreviewResponse,
  type ImportResult,
} from "@/features/comision/services/calificaciones";

export function usePreviewCalificaciones(materiaId: string) {
  return useMutation<PreviewResponse, Error, File>({
    mutationFn: (file: File) => previewCalificaciones(materiaId, file),
  });
}

export function useImportarCalificaciones(
  materiaId: string,
  previewToken: string,
) {
  return useMutation<ImportResult, Error, string[]>({
    mutationFn: (actividades: string[]) =>
      importarCalificaciones(materiaId, previewToken, actividades),
  });
}
