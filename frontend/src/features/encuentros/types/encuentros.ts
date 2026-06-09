import { z } from "zod";

export const InstanciaEstadoEnum = z.enum([
  "pendiente",
  "realizado",
  "cancelado",
]);

export const InstanciaSchema = z.object({
  id: z.string().uuid(),
  materia_id: z.string().uuid().nullable().optional(),
  slot_id: z.string().uuid().nullable().optional(),
  fecha: z.string(),
  hora: z.string().nullable().optional(),
  titulo: z.string().optional(),
  estado: InstanciaEstadoEnum,
  created_at: z.string().datetime().nullable().optional(),
  updated_at: z.string().datetime().nullable().optional(),
}).passthrough();

export type Instancia = z.infer<typeof InstanciaSchema>;

export const InstanciaListResponseSchema = z.object({
  items: z.array(InstanciaSchema),
  total: z.number(),
}).passthrough();

export type InstanciaListResponse = z.infer<typeof InstanciaListResponseSchema>;

export interface InstanciasFilters {
  materia_id?: string;
  slot_id?: string;
  desde?: string;
  hasta?: string;
  estado?: string;
}
