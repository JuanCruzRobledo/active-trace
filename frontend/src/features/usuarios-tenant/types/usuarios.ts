import { z } from "zod";

// ─── Usuario del Tenant ───────────────────────────────────────────────────────

export const UsuarioSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  nombre: z.string(),
  apellidos: z.string(),
  email: z.string(),
  dni: z.string().nullable().optional(),
  cuil: z.string().nullable().optional(),
  cbu: z.string().nullable().optional(),
  alias_cbu: z.string().nullable().optional(),
  banco: z.string().nullable().optional(),
  regional: z.string().nullable().optional(),
  legajo: z.string().nullable().optional(),
  legajo_profesional: z.string().nullable().optional(),
  facturador: z.string().nullable().optional(),
  estado: z.string(),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
}).passthrough();

export type Usuario = z.infer<typeof UsuarioSchema>;

export const UsuarioCreateSchema = z.object({
  nombre: z.string().min(1, "El nombre es obligatorio"),
  apellidos: z.string().min(1, "El apellido es obligatorio"),
  email: z.string().email("Email inválido"),
  dni: z.string().optional(),
  cuil: z.string().optional(),
  cbu: z.string().optional(),
  alias_cbu: z.string().optional(),
  banco: z.string().optional(),
  regional: z.string().optional(),
  legajo: z.string().optional(),
  legajo_profesional: z.string().optional(),
  facturador: z.string().optional(),
});

export type UsuarioCreate = z.infer<typeof UsuarioCreateSchema>;

export const UsuarioUpdateSchema = z.object({
  nombre: z.string().min(1).optional(),
  apellidos: z.string().min(1).optional(),
  email: z.string().email().optional(),
  dni: z.string().optional(),
  cuil: z.string().optional(),
  cbu: z.string().optional(),
  alias_cbu: z.string().optional(),
  banco: z.string().optional(),
  regional: z.string().optional(),
  legajo: z.string().optional(),
  legajo_profesional: z.string().optional(),
  facturador: z.string().optional(),
  estado: z.enum(["Activo", "Inactivo"]).optional(),
});

export type UsuarioUpdate = z.infer<typeof UsuarioUpdateSchema>;

export interface UsuariosFilters {
  estado?: string;
  nombre?: string;
}
