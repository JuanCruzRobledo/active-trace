import { z } from "zod";

// ─── Carrera ──────────────────────────────────────────────────────────────────

export const CarreraSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  codigo: z.string(),
  nombre: z.string(),
  activa: z.boolean().optional(),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
}).passthrough();

export type Carrera = z.infer<typeof CarreraSchema>;

export const CarreraCreateSchema = z.object({
  codigo: z.string().min(1, "El código es obligatorio"),
  nombre: z.string().min(1, "El nombre es obligatorio"),
}).strict();

export type CarreraCreate = z.infer<typeof CarreraCreateSchema>;

export const CarreraUpdateSchema = z.object({
  codigo: z.string().min(1).optional(),
  nombre: z.string().min(1).optional(),
  activa: z.boolean().optional(),
}).strict();

export type CarreraUpdate = z.infer<typeof CarreraUpdateSchema>;

// ─── Cohorte ──────────────────────────────────────────────────────────────────

export const CohorteSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  nombre: z.string(),
  anio: z.number().int().nullable().optional(),
  vigencia_desde: z.string().nullable().optional(),
  vigencia_hasta: z.string().nullable().optional(),
  activa: z.boolean().optional(),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
}).passthrough();

export type Cohorte = z.infer<typeof CohorteSchema>;

export const CohorteCreateSchema = z.object({
  nombre: z.string().min(1, "El nombre es obligatorio"),
  anio: z.number().int().optional(),
  vigencia_desde: z.string().optional(),
  vigencia_hasta: z.string().optional(),
}).strict();

export type CohorteCreate = z.infer<typeof CohorteCreateSchema>;

export const CohorteUpdateSchema = z.object({
  nombre: z.string().min(1).optional(),
  anio: z.number().int().optional(),
  vigencia_desde: z.string().optional(),
  vigencia_hasta: z.string().optional(),
  activa: z.boolean().optional(),
}).strict();

export type CohorteUpdate = z.infer<typeof CohorteUpdateSchema>;

// ─── Materia ──────────────────────────────────────────────────────────────────

export const MateriaSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  codigo: z.string(),
  nombre: z.string(),
  carrera_id: z.string().uuid().nullable().optional(),
  activa: z.boolean().optional(),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
}).passthrough();

export type Materia = z.infer<typeof MateriaSchema>;

export const MateriaCreateSchema = z.object({
  codigo: z.string().min(1, "El código es obligatorio"),
  nombre: z.string().min(1, "El nombre es obligatorio"),
  carrera_id: z.string().uuid().optional(),
}).strict();

export type MateriaCreate = z.infer<typeof MateriaCreateSchema>;

export const MateriaUpdateSchema = z.object({
  codigo: z.string().min(1).optional(),
  nombre: z.string().min(1).optional(),
  carrera_id: z.string().uuid().nullable().optional(),
  activa: z.boolean().optional(),
}).strict();

export type MateriaUpdate = z.infer<typeof MateriaUpdateSchema>;
