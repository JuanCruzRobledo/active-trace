import { api } from "@/shared/services/api";

export interface AtrasadoRow {
  alumno_id: string;
  alumno: string;
  legajo: string;
  actividades_faltantes: number;
  actividades_bajo_umbral: number;
  nota_actual: number | null;
  estado: "atrasado" | "al_dia";
  riesgo: "bajo" | "medio" | "alto";
}

export interface AtrasadosResponse {
  items: AtrasadoRow[];
  total: number;
}

export interface AtrasadosFilters {
  nombre?: string;
  actividad?: string;
  nota_min?: number;
  nota_max?: number;
}

/** Respuesta cruda del backend (antes del mapeo). */
interface BackendAtrasadosResponse {
  alumnos_atrasados: Array<{
    alumno_id: string;
    nombre: string;
    apellidos: string;
    actividades_faltantes: number;
    actividades_bajo_umbral: number;
    comision: string | null;
  }>;
  total_alumnos: number;
  porcentaje: number;
}

export async function getAtrasados(
  materiaId: string,
  filters?: AtrasadosFilters,
): Promise<AtrasadosResponse> {
  const params: Record<string, string> = {};
  if (filters?.nombre) params.nombre = filters.nombre;
  if (filters?.actividad) params.actividad = filters.actividad;
  if (filters?.nota_min !== undefined) params.nota_min = String(filters.nota_min);
  if (filters?.nota_max !== undefined) params.nota_max = String(filters.nota_max);
  const { data } = await api.get<BackendAtrasadosResponse>(
    `/analisis/atrasados`,
    { params: { ...params, materia_id: materiaId } },
  );

  const items: AtrasadoRow[] = data.alumnos_atrasados.map((entry) => {
    const riesgo: AtrasadoRow["riesgo"] =
      entry.actividades_bajo_umbral >= 2
        ? "alto"
        : entry.actividades_bajo_umbral === 1
          ? "medio"
          : "bajo";
    return {
      alumno_id: entry.alumno_id,
      alumno: `${entry.nombre} ${entry.apellidos}`,
      legajo: "", // el backend no expone legajo todavía
      actividades_faltantes: entry.actividades_faltantes,
      actividades_bajo_umbral: entry.actividades_bajo_umbral,
      nota_actual: null, // el backend no expone nota_actual todavía
      estado: "atrasado",
      riesgo,
    };
  });

  return { items, total: data.total_alumnos };
}
