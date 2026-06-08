import { api } from "@/shared/services/api";
import type {
  AccionPorDia,
  ComunicacionPorDocente,
  InteraccionPorDocenteMateria,
  UltimaAccion,
  LogResponse,
  AuditoriaFilters,
  LogFilters,
} from "@/features/auditoria/types/auditoria";

export async function fetchAccionesPorDia(
  filters?: AuditoriaFilters,
): Promise<AccionPorDia[]> {
  const params: Record<string, string> = {};
  if (filters?.fecha_desde) params.fecha_desde = filters.fecha_desde;
  if (filters?.fecha_hasta) params.fecha_hasta = filters.fecha_hasta;
  if (filters?.materia_id) params.materia_id = filters.materia_id;
  const { data } = await api.get<AccionPorDia[]>(
    "/auditoria/acciones-por-dia",
    { params },
  );
  return data;
}

export async function fetchComunicacionesPorDocente(
  filters?: AuditoriaFilters,
): Promise<ComunicacionPorDocente[]> {
  const params: Record<string, string> = {};
  if (filters?.materia_id) params.materia_id = filters.materia_id;
  if (filters?.fecha_desde) params.fecha_desde = filters.fecha_desde;
  if (filters?.fecha_hasta) params.fecha_hasta = filters.fecha_hasta;
  const { data } = await api.get<ComunicacionPorDocente[]>(
    "/auditoria/comunicaciones-por-docente",
    { params },
  );
  return data;
}

export async function fetchInteraccionesPorDocenteMateria(
  filters?: AuditoriaFilters,
): Promise<InteraccionPorDocenteMateria[]> {
  const params: Record<string, string> = {};
  if (filters?.fecha_desde) params.fecha_desde = filters.fecha_desde;
  if (filters?.fecha_hasta) params.fecha_hasta = filters.fecha_hasta;
  const { data } = await api.get<InteraccionPorDocenteMateria[]>(
    "/auditoria/interacciones-por-docente-materia",
    { params },
  );
  return data;
}

export async function fetchUltimasAcciones(limit?: number): Promise<UltimaAccion[]> {
  const params: Record<string, string> = {};
  if (limit !== undefined) params.limit = String(limit);
  const { data } = await api.get<UltimaAccion[]>("/auditoria/ultimas-acciones", {
    params,
  });
  return data;
}

export async function fetchLog(filters?: LogFilters): Promise<LogResponse> {
  const params: Record<string, string> = {};
  if (filters?.fecha_desde) params.fecha_desde = filters.fecha_desde;
  if (filters?.fecha_hasta) params.fecha_hasta = filters.fecha_hasta;
  if (filters?.materia_id) params.materia_id = filters.materia_id;
  if (filters?.usuario_id) params.usuario_id = filters.usuario_id;
  if (filters?.accion) params.accion = filters.accion;
  if (filters?.offset !== undefined) params.offset = String(filters.offset);
  if (filters?.limit !== undefined) params.limit = String(filters.limit);
  const { data } = await api.get<LogResponse>("/auditoria/log", { params });
  return data;
}
