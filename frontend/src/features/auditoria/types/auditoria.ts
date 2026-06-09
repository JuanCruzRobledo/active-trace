import { z } from "zod";

// ─── Acciones por Día ─────────────────────────────────────────────────────────

export const AccionPorDiaSchema = z.object({
  fecha: z.string(),
  total: z.number().int(),
}).passthrough();

export type AccionPorDia = z.infer<typeof AccionPorDiaSchema>;

// ─── Comunicaciones por Docente ───────────────────────────────────────────────

export const ComunicacionPorDocenteSchema = z.object({
  usuario_id: z.string().uuid(),
  nombre: z.string(),
  Pendiente: z.number().int().optional(),
  Enviando: z.number().int().optional(),
  OK: z.number().int().optional(),
  Fallido: z.number().int().optional(),
  Cancelado: z.number().int().optional(),
}).passthrough();

export type ComunicacionPorDocente = z.infer<typeof ComunicacionPorDocenteSchema>;

// ─── Interacciones por Docente-Materia ────────────────────────────────────────

export const InteraccionPorDocenteMateriaSchema = z.object({
  usuario_id: z.string().uuid(),
  nombre: z.string(),
  materia_id: z.string().uuid(),
  materia_nombre: z.string(),
  acciones: z.record(z.string(), z.number().int()),
  total: z.number().int(),
}).passthrough();

export type InteraccionPorDocenteMateria = z.infer<
  typeof InteraccionPorDocenteMateriaSchema
>;

// ─── Última Acción ────────────────────────────────────────────────────────────

export const UltimaAccionSchema = z.object({
  id: z.string().uuid(),
  fecha_hora: z.string().nullable().optional(),
  actor_nombre: z.string().nullable().optional(),
  accion: z.string(),
  materia_nombre: z.string().nullable().optional(),
  detalle: z.any().optional(),
  ip: z.string().nullable().optional(),
}).passthrough();

export type UltimaAccion = z.infer<typeof UltimaAccionSchema>;

// ─── Log Item ─────────────────────────────────────────────────────────────────

export const LogItemSchema = z.object({
  id: z.string().uuid(),
  fecha_hora: z.string().nullable().optional(),
  actor_id: z.string().uuid().nullable().optional(),
  actor_nombre: z.string().nullable().optional(),
  materia_id: z.string().uuid().nullable().optional(),
  materia_nombre: z.string().nullable().optional(),
  accion: z.string(),
  detalle: z.any().optional(),
  filas_afectadas: z.number().int().nullable().optional(),
  ip: z.string().nullable().optional(),
  user_agent: z.string().nullable().optional(),
}).passthrough();

export type LogItem = z.infer<typeof LogItemSchema>;

export const LogResponseSchema = z.object({
  items: z.array(LogItemSchema),
  total: z.number().int(),
}).passthrough();

export type LogResponse = z.infer<typeof LogResponseSchema>;

// ─── Filtros ──────────────────────────────────────────────────────────────────

export interface AuditoriaFilters {
  fecha_desde?: string;
  fecha_hasta?: string;
  materia_id?: string;
}

export interface LogFilters extends AuditoriaFilters {
  usuario_id?: string;
  accion?: string;
  offset?: number;
  limit?: number;
}
