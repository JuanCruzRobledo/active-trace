import { z } from "zod";

// ─── Carrera ──────────────────────────────────────────────────────────────────

export const CarreraSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  codigo: z.string(),
  nombre: z.string(),
  estado: z.string().optional(),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
}).passthrough();

export type Carrera = z.infer<typeof CarreraSchema>;

export const CarreraCreateSchema = z.object({
  codigo: z.string().min(1, "El código es obligatorio"),
  nombre: z.string().min(1, "El nombre es obligatorio"),
  estado: z.string().optional(),
}).strict();

export type CarreraCreate = z.infer<typeof CarreraCreateSchema>;

export const CarreraUpdateSchema = z.object({
  nombre: z.string().min(1).optional(),
  estado: z.string().optional(),
}).strict();

export type CarreraUpdate = z.infer<typeof CarreraUpdateSchema>;

// ─── Cohorte ──────────────────────────────────────────────────────────────────

export const CohorteSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  carrera_id: z.string().nullable().optional(),
  nombre: z.string(),
  anio: z.number().int().nullable().optional(),
  vig_desde: z.string().nullable().optional(),
  vig_hasta: z.string().nullable().optional(),
  estado: z.string().optional(),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
}).passthrough();

export type Cohorte = z.infer<typeof CohorteSchema>;

export const CohorteCreateSchema = z.object({
  carrera_id: z.string().min(1, "La carrera es obligatoria"),
  nombre: z.string().min(1, "El nombre es obligatorio"),
  anio: z.number().int(),
  vig_desde: z.string().min(1, "La fecha de inicio es obligatoria"),
  vig_hasta: z.string().optional(),
  estado: z.string().optional(),
}).strict();

export type CohorteCreate = z.infer<typeof CohorteCreateSchema>;

export const CohorteUpdateSchema = z.object({
  nombre: z.string().min(1).optional(),
  vig_desde: z.string().optional(),
  vig_hasta: z.string().optional(),
  estado: z.string().optional(),
}).strict();

export type CohorteUpdate = z.infer<typeof CohorteUpdateSchema>;

// ─── Materia ──────────────────────────────────────────────────────────────────

export const MateriaSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  codigo: z.string(),
  nombre: z.string(),
  carrera_id: z.string().uuid().nullable().optional(),
  estado: z.string().optional(),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
}).passthrough();

export type Materia = z.infer<typeof MateriaSchema>;

export const MateriaCreateSchema = z.object({
  codigo: z.string().min(1, "El código es obligatorio"),
  nombre: z.string().min(1, "El nombre es obligatorio"),
  estado: z.string().optional(),
}).strict();

export type MateriaCreate = z.infer<typeof MateriaCreateSchema>;

export const MateriaUpdateSchema = z.object({
  nombre: z.string().min(1).optional(),
  estado: z.string().optional(),
}).strict();

export type MateriaUpdate = z.infer<typeof MateriaUpdateSchema>;
