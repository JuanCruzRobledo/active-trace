import { api } from "@/shared/services/api";

export interface MonitorRow {
  alumno_id: string;
  alumno: string;
  correo: string;
  comision: string;
  actividad: string;
  estado: string;
  nota: number | null;
  materia: string;
}

export interface MonitoresResponse {
  items: MonitorRow[];
  total: number;
}

export interface MonitoresFilters {
  nombre?: string;
  correo?: string;
  comision?: string;
  materia?: string;
  actividad?: string;
  actividades_min?: number;
  fecha_desde?: string;
  fecha_hasta?: string;
}

/** Respuesta cruda del backend */
interface BackendMonitorResponse {
  alumnos: Array<{
    alumno_id: string;
    nombre: string;
    apellidos: string;
    comision: string | null;
    email: string | null;
    actividades: Array<{
      actividad: string;
      nota_numerica: number | null;
      nota_textual: string | null;
      aprobado: boolean | null;
      materia_nombre: string | null;
    }>;
  }>;
  total: number;
}

export async function getMonitores(
  filters?: MonitoresFilters,
): Promise<MonitoresResponse> {
  const params: Record<string, string> = {};
  // El backend soporta actividad, min_aprobadas, fecha_desde, fecha_hasta; el resto se filtra en cliente
  if (filters?.actividad) params.actividad = filters.actividad;
  if (filters?.actividades_min !== undefined) {
    params.min_aprobadas = String(filters.actividades_min);
  }
  if (filters?.fecha_desde) params.fecha_desde = filters.fecha_desde;
  if (filters?.fecha_hasta) params.fecha_hasta = filters.fecha_hasta;
  const { data } = await api.get<BackendMonitorResponse>(
    `/analisis/monitor-seguimiento`,
    { params },
  );

  // Aplana: cada alumno → filas (una por actividad), deduplicando (alumno_id + actividad)
  const seen = new Set<string>();
  const items: MonitorRow[] = [];
  for (const alumno of data.alumnos) {
    for (const act of alumno.actividades) {
      const key = `${alumno.alumno_id}|${act.actividad}`;
      if (seen.has(key)) continue;
      seen.add(key);

      const estado =
        act.aprobado === true
          ? "aprobada"
          : act.aprobado === false
            ? "pendiente"
            : "sin_dato";

      // Filtros del lado cliente
      if (filters?.nombre) {
        const fullName = `${alumno.nombre} ${alumno.apellidos}`.toLowerCase();
        if (!fullName.includes(filters.nombre.toLowerCase())) continue;
      }
      if (filters?.correo) {
        const email = (alumno.email ?? "").toLowerCase();
        if (!email.includes(filters.correo.toLowerCase())) continue;
      }
      if (filters?.comision && alumno.comision?.toLowerCase() !== filters.comision.toLowerCase()) continue;
      if (filters?.materia) {
        const materia = (act.materia_nombre ?? "").toLowerCase();
        if (!materia.includes(filters.materia.toLowerCase())) continue;
      }

      items.push({
        alumno_id: alumno.alumno_id,
        alumno: `${alumno.nombre} ${alumno.apellidos}`,
        correo: alumno.email ?? "",
        comision: alumno.comision ?? "",
        materia: act.materia_nombre ?? "",
        actividad: act.actividad,
        estado,
        nota: act.nota_numerica,
      });
    }
  }

  return { items, total: items.length };
}

/** @deprecated No existe endpoint de exportación en backend. */
export async function exportarMonitores(
  _filters?: MonitoresFilters,
): Promise<Blob> {
  console.warn("exportarMonitores no implementado en backend");
  return new Blob([]);
}
