import { z } from "zod";

export const TareaEstadoEnum = z.enum([
  "Pendiente",
  "En progreso",
  "Resuelta",
  "Cancelada",
]);

export const TareaSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  materia_id: z.string().uuid().nullable().optional(),
  asignado_a: z.string().uuid(),
  asignado_por: z.string().uuid(),
  estado: TareaEstadoEnum,
  descripcion: z.string(),
  contexto_id: z.string().uuid().nullable().optional(),
  created_at: z.string().datetime().nullable().optional(),
  updated_at: z.string().datetime().nullable().optional(),
}).passthrough();

export type Tarea = z.infer<typeof TareaSchema>;

export const ComentarioSchema = z.object({
  id: z.string().uuid(),
  tarea_id: z.string().uuid(),
  autor_id: z.string().uuid(),
  texto: z.string(),
  creado_at: z.string().datetime().nullable().optional(),
}).passthrough();

export type Comentario = z.infer<typeof ComentarioSchema>;

export const TareaConComentariosSchema = TareaSchema.extend({
  comentarios: z.array(ComentarioSchema),
});

export type TareaConComentarios = z.infer<typeof TareaConComentariosSchema>;

export const TareaCreateSchema = z.object({
  materia_id: z.string().uuid().nullable().optional(),
  asignado_a: z.string().uuid("Seleccioná un docente"),
  descripcion: z.string().min(1, "La descripción es obligatoria"),
}).strict();

export type TareaCreate = z.infer<typeof TareaCreateSchema>;

export const TareaEstadoUpdateSchema = z.object({
  nuevo_estado: TareaEstadoEnum,
}).strict();

export type TareaEstadoUpdate = z.infer<typeof TareaEstadoUpdateSchema>;

export const ComentarioCreateSchema = z.object({
  texto: z.string().min(1, "El comentario no puede estar vacío"),
}).strict();

export type ComentarioCreate = z.infer<typeof ComentarioCreateSchema>;

export const TareaListResponseSchema = z.object({
  items: z.array(TareaSchema),
  total: z.number(),
}).passthrough();

export type TareaListResponse = z.infer<typeof TareaListResponseSchema>;

export interface TareasFilters {
  estado?: string;
  materia_id?: string;
  asignado_a?: string;
  asignado_por?: string;
  busqueda?: string;
}
