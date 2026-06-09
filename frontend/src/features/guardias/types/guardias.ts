import { z } from "zod";

export const GuardiaSchema = z.object({
  id: z.string().uuid(),
  asignacion_id: z.string().uuid().nullable().optional(),
  materia_id: z.string().uuid().nullable().optional(),
  carrera_id: z.string().uuid().nullable().optional(),
  cohorte_id: z.string().uuid().nullable().optional(),
  dia: z.string(),
  horario: z.string(),
  estado: z.string(),
  comentarios: z.string().optional().nullable(),
  creada_at: z.string().nullable().optional(),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
  docente_nombre: z.string().nullable().optional(),
}).passthrough();

export type Guardia = z.infer<typeof GuardiaSchema>;

export const GuardiaCreateSchema = z.object({
  dia: z.string().min(1, "El día es obligatorio"),
  horario: z.string().min(1, "El horario es obligatorio"),
  estado: z.string().optional(),
  comentarios: z.string().optional().nullable(),
  materia_id: z.string().uuid("Seleccioná una materia").optional(),
  carrera_id: z.string().uuid("Seleccioná una carrera").optional(),
  cohorte_id: z.string().uuid("Seleccioná un cohorte").optional(),
}).passthrough();

export type GuardiaCreate = z.infer<typeof GuardiaCreateSchema>;

export const GuardiaUpdateSchema = z.object({
  estado: z.string().optional(),
  comentarios: z.string().optional().nullable(),
}).passthrough();

export type GuardiaUpdate = z.infer<typeof GuardiaUpdateSchema>;

export interface GuardiaFilters {
  materia_id?: string;
  usuario_id?: string;
  desde?: string;
  hasta?: string;
  estado?: string;
}

export interface GuardiasResponse {
  items: Guardia[];
  total: number;
}
