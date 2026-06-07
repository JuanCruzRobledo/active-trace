import { z } from "zod";

export const FechaAcademicaSchema = z.object({
  id: z.string().uuid(),
  materia_id: z.string().uuid(),
  cohorte_id: z.string().uuid().optional().nullable(),
  tipo: z.string(),
  titulo: z.string(),
  fecha_evaluacion: z.string(),
  numero_instancia: z.number().int().optional().nullable(),
  creado_en: z.string(),
  actualizado_en: z.string(),
});

export const FechaAcademicaCreateSchema = z.object({
  materia_id: z.string().uuid("Seleccioná una materia"),
  cohorte_id: z.string().uuid().optional().nullable(),
  tipo: z.string().min(1, "El tipo es obligatorio"),
  titulo: z.string().min(1, "El título es obligatorio"),
  fecha_evaluacion: z.string().min(1, "La fecha es obligatoria"),
  numero_instancia: z.number().int().optional().nullable(),
}).strict();

export const FechaAcademicaUpdateSchema = FechaAcademicaCreateSchema.partial();

export type FechaAcademica = z.infer<typeof FechaAcademicaSchema>;
export type FechaAcademicaCreate = z.input<typeof FechaAcademicaCreateSchema>;
export type FechaAcademicaUpdate = z.input<typeof FechaAcademicaUpdateSchema>;

export interface FechaAcademicaFilters {
  materia_id?: string;
  cohorte_id?: string;
  tipo?: string;
  periodo?: string;
}

export interface FechasAcademicasResponse {
  items: FechaAcademica[];
  total: number;
}
