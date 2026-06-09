import { z } from "zod";

export const AvisoCreateSchema = z.object({
  alcance: z.enum(["Global", "PorMateria", "PorCohorte", "PorRol"]),
  materia_id: z.string().uuid().optional(),
  cohorte_id: z.string().uuid().optional(),
  rol_destino: z.string().optional(),
  severidad: z.enum(["Info", "Advertencia", "Crítico"]),
  titulo: z.string().min(1).max(200),
  cuerpo: z.string().min(1),
  inicio_en: z.string(),
  fin_en: z.string(),
  orden: z.number().int().default(0),
  requiere_ack: z.boolean().default(false),
}).strict();

export type AvisoCreate = z.infer<typeof AvisoCreateSchema>;

export const AvisoUpdateSchema = z.object({
  alcance: z.enum(["Global", "PorMateria", "PorCohorte", "PorRol"]).optional(),
  materia_id: z.string().uuid().optional(),
  cohorte_id: z.string().uuid().optional(),
  rol_destino: z.string().optional(),
  severidad: z.enum(["Info", "Advertencia", "Crítico"]).optional(),
  titulo: z.string().min(1).max(200).optional(),
  cuerpo: z.string().min(1).optional(),
  inicio_en: z.string().optional(),
  fin_en: z.string().optional(),
  orden: z.number().int().optional(),
  requiere_ack: z.boolean().optional(),
  activo: z.boolean().optional(),
}).strict();

export type AvisoUpdate = z.infer<typeof AvisoUpdateSchema>;

export const AvisoResponseSchema = z.object({
  id: z.string().uuid(),
  alcance: z.string(),
  materia_id: z.string().uuid().nullable().optional(),
  cohorte_id: z.string().uuid().nullable().optional(),
  rol_destino: z.string().nullable().optional(),
  severidad: z.string(),
  titulo: z.string(),
  cuerpo: z.string(),
  inicio_en: z.string(),
  fin_en: z.string(),
  orden: z.number().int(),
  activo: z.boolean(),
  requiere_ack: z.boolean(),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
  total_ack: z.number().int(),
  total_usuarios_alcance: z.number().int(),
  porcentaje_ack: z.number(),
});

export type AvisoResponse = z.infer<typeof AvisoResponseSchema>;

export const AvisoTimelineItemSchema = z.object({
  id: z.string().uuid(),
  alcance: z.string(),
  severidad: z.string(),
  titulo: z.string(),
  cuerpo: z.string(),
  inicio_en: z.string(),
  fin_en: z.string(),
  orden: z.number().int(),
  requiere_ack: z.boolean(),
  acknowledged: z.boolean(),
  created_at: z.string().nullable().optional(),
});

export type AvisoTimelineItem = z.infer<typeof AvisoTimelineItemSchema>;

export const TrackingAvisoResponseSchema = z.object({
  total_usuarios: z.number().int(),
  total_ack: z.number().int(),
  porcentaje: z.number(),
  acknowledgments: z.array(
    z.object({
      usuario_id: z.string().uuid(),
      usuario_nombre: z.string().nullable().optional(),
      confirmado_at: z.string().nullable().optional(),
    }),
  ),
});

export type TrackingAvisoResponse = z.infer<typeof TrackingAvisoResponseSchema>;

export interface AvisoFilters {
  materia_id?: string;
  cohorte_id?: string;
  alcance?: string;
  severidad?: string;
  activo?: boolean;
}
