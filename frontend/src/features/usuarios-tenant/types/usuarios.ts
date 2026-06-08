import { z } from "zod";

// ─── Usuario del Tenant ───────────────────────────────────────────────────────

export const UsuarioRolEnum = z.enum([
  "TUTOR",
  "NEXO",
  "COORDINADOR",
  "ADMIN",
  "SOPORTE",
]);

export const UsuarioModalidadEnum = z.enum(["presencial", "virtual", "mixta"]);

export const UsuarioSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  email: z.string().email(),
  nombre: z.string(),
  apellido: z.string().nullable().optional(),
  rol: z.string().nullable().optional(),
  modalidad: z.string().nullable().optional(),
  activo: z.boolean().optional(),
  // Datos fiscales
  cuit: z.string().nullable().optional(),
  condicion_fiscal: z.string().nullable().optional(),
  // Datos bancarios
  cbu: z.string().nullable().optional(),
  alias: z.string().nullable().optional(),
  banco: z.string().nullable().optional(),
  // Regional
  regional: z.string().nullable().optional(),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
}).passthrough();

export type Usuario = z.infer<typeof UsuarioSchema>;

export const UsuarioCreateSchema = z.object({
  email: z.string().email("Email inválido"),
  nombre: z.string().min(1, "El nombre es obligatorio"),
  apellido: z.string().optional(),
  rol: z.string().optional(),
  modalidad: z.string().optional(),
  cuit: z.string().optional(),
  condicion_fiscal: z.string().optional(),
  cbu: z.string().optional(),
  alias: z.string().optional(),
  banco: z.string().optional(),
  regional: z.string().optional(),
}).strict();

export type UsuarioCreate = z.infer<typeof UsuarioCreateSchema>;

export const UsuarioUpdateSchema = z.object({
  nombre: z.string().min(1).optional(),
  apellido: z.string().optional(),
  rol: z.string().optional(),
  modalidad: z.string().optional(),
  activo: z.boolean().optional(),
  cuit: z.string().optional(),
  condicion_fiscal: z.string().optional(),
  cbu: z.string().optional(),
  alias: z.string().optional(),
  banco: z.string().optional(),
  regional: z.string().optional(),
}).strict();

export type UsuarioUpdate = z.infer<typeof UsuarioUpdateSchema>;

export interface UsuariosFilters {
  rol?: string;
  activo?: boolean;
  busqueda?: string;
}
