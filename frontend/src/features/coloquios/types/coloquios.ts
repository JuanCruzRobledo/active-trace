import { z } from "zod";

export const EvaluacionSchema = z.object({
  id: z.string().uuid(),
  materia_id: z.string().uuid(),
  cohorte_id: z.string().uuid().nullable().optional(),
  titulo: z.string(),
  estado: z.string(),
  fechas_disponibles: z.any().nullable().optional(),
  cupos_por_dia: z.number().int().nullable().optional(),
  created_at: z.string().datetime().nullable().optional(),
  updated_at: z.string().datetime().nullable().optional(),
}).passthrough();

export type Evaluacion = z.infer<typeof EvaluacionSchema>;

export const EvaluacionCreateSchema = z.object({
  materia_id: z.string().uuid("Seleccioná una materia"),
  cohorte_id: z.string().uuid().nullable().optional(),
  titulo: z.string().min(1, "El título es obligatorio"),
  fechas_disponibles: z.any().nullable().optional(),
  cupos_por_dia: z.number().int().positive().nullable().optional(),
}).strict();

export type EvaluacionCreate = z.infer<typeof EvaluacionCreateSchema>;

export interface EvaluacionUpdate {
  titulo?: string;
  estado?: string;
  fechas_disponibles?: unknown;
  cupos_por_dia?: number | null;
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
    titulo: z.string().optional(),
    estado: z.string().optional(),
    fechas_disponibles: z.any().optional(),
    cupos_por_dia: z.number().int().optional().nullable(),
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
