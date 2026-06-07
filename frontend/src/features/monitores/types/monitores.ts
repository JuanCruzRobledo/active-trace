import { z } from "zod";

export const EstadoGeneralEnum = z.enum(["al_dia", "en_seguimiento", "critico"]);

export type EstadoGeneral = z.infer<typeof EstadoGeneralEnum>;

export const MonitorGeneralFiltersSchema = z.object({
  materia_id: z.string().uuid().optional(),
  regional: z.string().optional(),
  comision: z.string().optional(),
  q: z.string().optional(),
}).strict();

export type MonitorGeneralFilters = z.infer<typeof MonitorGeneralFiltersSchema>;

export const AlumnoGeneralRowSchema = z.object({
  alumno_id: z.string(),
  alumno: z.string(),
  correo: z.string(),
  comision: z.string(),
  materia: z.string(),
  total_actividades: z.number(),
  aprobadas: z.number(),
  pendientes: z.number(),
  ultima_actividad: z.string(),
  estado_general: EstadoGeneralEnum,
}).strict();

export type AlumnoGeneralRow = z.infer<typeof AlumnoGeneralRowSchema>;

export const MonitorGeneralResponseSchema = z.object({
  items: z.array(AlumnoGeneralRowSchema),
  total: z.number(),
}).strict();

export type MonitorGeneralResponse = z.infer<typeof MonitorGeneralResponseSchema>;
