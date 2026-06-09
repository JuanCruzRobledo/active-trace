import { z } from "zod";

export const EquipoResponseSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  usuario_id: z.string().uuid(),
  rol: z.string(),
  materia_id: z.string().uuid().nullable().optional(),
  carrera_id: z.string().uuid().nullable().optional(),
  cohorte_id: z.string().uuid().nullable().optional(),
  comisiones: z.array(z.string()).nullable().optional(),
  responsable_id: z.string().uuid().nullable().optional(),
  desde: z.string(),
  hasta: z.string().nullable().optional(),
  estado_vigencia: z.string(),
  materia_nombre: z.string().nullable().optional(),
  carrera_nombre: z.string().nullable().optional(),
  cohorte_nombre: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type EquipoResponse = z.infer<typeof EquipoResponseSchema>;

export const AsignacionMasivaRequestSchema = z.object({
  usuario_ids: z.array(z.string().uuid()),
  materia_id: z.string().uuid(),
  carrera_id: z.string().uuid(),
  cohorte_id: z.string().uuid(),
  rol: z.string(),
  comisiones: z.array(z.string()).optional(),
  responsable_id: z.string().uuid().optional(),
  desde: z.string(),
  hasta: z.string().optional(),
}).strict();

export type AsignacionMasivaRequest = z.infer<typeof AsignacionMasivaRequestSchema>;

export const ClonarEquipoRequestSchema = z.object({
  origen_materia_id: z.string().uuid(),
  origen_carrera_id: z.string().uuid(),
  origen_cohorte_id: z.string().uuid(),
  destino_materia_id: z.string().uuid(),
  destino_carrera_id: z.string().uuid(),
  destino_cohorte_id: z.string().uuid(),
  destino_desde: z.string(),
  destino_hasta: z.string().optional(),
}).strict();

export type ClonarEquipoRequest = z.infer<typeof ClonarEquipoRequestSchema>;

export const VigenciaRequestSchema = z.object({
  materia_id: z.string().uuid(),
  carrera_id: z.string().uuid(),
  cohorte_id: z.string().uuid(),
  desde: z.string(),
  hasta: z.string().optional(),
}).strict();

export type VigenciaRequest = z.infer<typeof VigenciaRequestSchema>;

export interface VigenciaResponse {
  afectadas: number;
  desde: string;
  hasta?: string | null;
}

export interface ClonarResponse {
  creadas: number;
  origen: string;
  destino: string;
  asignaciones: any[];
}

export interface EquipoFilters {
  materia_id?: string;
  carrera_id?: string;
  cohorte_id?: string;
  usuario_id?: string;
  rol?: string;
  vigente?: boolean;
}
