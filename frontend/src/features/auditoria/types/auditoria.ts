import { z } from "zod";

// ─── Acciones por Día ─────────────────────────────────────────────────────────

export const AccionPorDiaSchema = z.object({
  fecha: z.string(),
  cantidad: z.number().int(),
  materia_id: z.string().uuid().nullable().optional(),
}).passthrough();

export type AccionPorDia = z.infer<typeof AccionPorDiaSchema>;

// ─── Comunicaciones por Docente ───────────────────────────────────────────────

export const ComunicacionPorDocenteSchema = z.object({
  usuario_id: z.string().uuid(),
  nombre: z.string().nullable().optional(),
  cantidad: z.number().int(),
  materia_id: z.string().uuid().nullable().optional(),
}).passthrough();

export type ComunicacionPorDocente = z.infer<typeof ComunicacionPorDocenteSchema>;

// ─── Interacciones por Docente-Materia ────────────────────────────────────────

export const InteraccionPorDocenteMateriaSchema = z.object({
  usuario_id: z.string().uuid(),
  materia_id: z.string().uuid(),
  nombre_usuario: z.string().nullable().optional(),
  nombre_materia: z.string().nullable().optional(),
  cantidad: z.number().int(),
}).passthrough();

export type InteraccionPorDocenteMateria = z.infer<
  typeof InteraccionPorDocenteMateriaSchema
>;

// ─── Última Acción ────────────────────────────────────────────────────────────

export const UltimaAccionSchema = z.object({
  id: z.string().uuid(),
  usuario_id: z.string().uuid().nullable().optional(),
  materia_id: z.string().uuid().nullable().optional(),
  accion: z.string(),
  registros: z.number().int().nullable().optional(),
  ip: z.string().nullable().optional(),
  user_agent: z.string().nullable().optional(),
  created_at: z.string().nullable().optional(),
}).passthrough();

export type UltimaAccion = z.infer<typeof UltimaAccionSchema>;

// ─── Log Item ─────────────────────────────────────────────────────────────────

export const LogItemSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid().nullable().optional(),
  usuario_id: z.string().uuid().nullable().optional(),
  materia_id: z.string().uuid().nullable().optional(),
  accion: z.string(),
  registros: z.number().int().nullable().optional(),
  ip: z.string().nullable().optional(),
  user_agent: z.string().nullable().optional(),
  created_at: z.string().nullable().optional(),
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
