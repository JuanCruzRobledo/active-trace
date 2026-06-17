import { z } from "zod";

export const EvaluacionSchema = z.object({
  id: z.string().uuid(),
  materia_id: z.string().uuid(),
  cohorte_id: z.string().uuid(),
  tipo: z.string(),
  instancia: z.string(),
  dias_disponibles: z.number().int(),
  cupos_por_dia: z.number().int(),
  fecha_inicio: z.string(),
  fecha_fin: z.string(),
  estado: z.string(),
  created_at: z.string().datetime().nullable().optional(),
  updated_at: z.string().datetime().nullable().optional(),
  convocados: z.number().int().optional(),
  reservas_activas: z.number().int().optional(),
  cupos_libres: z.number().int().optional(),
  resultados: z.number().int().optional(),
}).passthrough();

export type Evaluacion = z.infer<typeof EvaluacionSchema>;

export const EvaluacionCreateSchema = z.object({
  materia_id: z.string().uuid("Seleccioná una materia"),
  cohorte_id: z.string().uuid("Seleccioná un cohorte"),
  tipo: z.string().min(1, "Seleccioná un tipo de evaluación"),
  instancia: z.string().min(1, "La instancia es obligatoria"),
  dias_disponibles: z.coerce.number().int().positive("Debe ser mayor a 0").default(1),
  cupos_por_dia: z.coerce.number().int().positive("Debe ser mayor a 0").default(1),
  fecha_inicio: z.string().min(1, "La fecha de inicio es obligatoria"),
  fecha_fin: z.string().min(1, "La fecha de fin es obligatoria"),
}).strict();

export type EvaluacionCreate = z.infer<typeof EvaluacionCreateSchema>;

export interface EvaluacionUpdate {
  instancia?: string;
  dias_disponibles?: number;
  cupos_por_dia?: number | null;
  fecha_inicio?: string;
  fecha_fin?: string;
}

export interface ImportarAlumnosRequest {
  alumno_ids?: string[];
}

export interface MetricasColoquios {
  total_evaluaciones: number;
  activas: number;
  total_alumnos_convocados: number;
  total_reservas: number;
  notas_cargadas: number;
}

export interface AgendaItem {
  evaluacion_id: string;
  titulo: string;
  fecha: string;
  alumno: string;
  estado: string;
}

export function createEvaluacionUpdateSchema(): z.ZodSchema {
  return z.object({
    instancia: z.string().optional(),
    dias_disponibles: z.number().int().optional(),
    cupos_por_dia: z.number().int().optional().nullable(),
    fecha_inicio: z.string().optional(),
    fecha_fin: z.string().optional(),
  }).strict();
}

export interface ConvocatoriasFilters {
  materia_id?: string;
  cohorte_id?: string;
  estado?: string;
}

export const ConvocatoriasListResponseSchema = z.object({
  items: z.array(EvaluacionSchema),
  total: z.number(),
}).passthrough();

export type ConvocatoriasListResponse = z.infer<typeof ConvocatoriasListResponseSchema>;
