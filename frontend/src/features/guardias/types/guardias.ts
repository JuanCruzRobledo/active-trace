import { z } from "zod";

export const GuardiaSchema = z.object({
  id: z.string().uuid(),
  materia_id: z.string().uuid(),
  usuario_id: z.string().uuid(),
  fecha: z.string(),
  hora_inicio: z.string(),
  hora_fin: z.string(),
  estado: z.string().default("pendiente"),
  comentarios: z.string().optional().nullable(),
  creado_en: z.string(),
  actualizado_en: z.string(),
});

const guardiaCreateBase = z.object({
  materia_id: z.string().uuid("Seleccioná una materia"),
  fecha: z.string().min(1, "La fecha es obligatoria"),
  hora_inicio: z.string().min(1, "La hora de inicio es obligatoria"),
  hora_fin: z.string().min(1, "La hora de fin es obligatoria"),
  estado: z.string().optional(),
  comentarios: z.string().optional().nullable(),
}).strict();

export const GuardiaCreateSchema = guardiaCreateBase.refine(
  (data) => !data.hora_inicio || !data.hora_fin || data.hora_inicio < data.hora_fin,
  { message: "La hora de fin debe ser posterior a la de inicio", path: ["hora_fin"] },
);

export const GuardiaUpdateSchema = guardiaCreateBase.partial();

export type Guardia = z.infer<typeof GuardiaSchema>;
export type GuardiaCreate = z.input<typeof GuardiaCreateSchema>;
export type GuardiaUpdate = z.input<typeof GuardiaUpdateSchema>;

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
