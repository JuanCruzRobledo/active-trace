import { z } from "zod";

export const ProgramaSchema = z.object({
  id: z.string().uuid(),
  materia_id: z.string().uuid(),
  carrera_id: z.string().uuid().optional().nullable(),
  cohorte_id: z.string().uuid().optional().nullable(),
  nombre: z.string(),
  archivo_url: z.string(),
  tipo: z.string().optional().nullable(),
  subido_en: z.string(),
  subido_por: z.string().uuid(),
});

export type Programa = z.infer<typeof ProgramaSchema>;

export interface ProgramaFilters {
  materia_id?: string;
  carrera_id?: string;
  cohorte_id?: string;
}

export interface ProgramasResponse {
  items: Programa[];
  total: number;
}
