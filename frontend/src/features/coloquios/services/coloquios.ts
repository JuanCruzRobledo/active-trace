import { api } from "@/shared/services/api";
import type {
  Evaluacion,
  EvaluacionCreate,
  EvaluacionUpdate,
  ImportarAlumnosRequest,
  MetricasColoquios,
  AgendaItem,
  ConvocatoriasFilters,
  ConvocatoriasListResponse,
} from "@/features/coloquios/types/coloquios";

export async function fetchMetricas(): Promise<MetricasColoquios> {
  const { data } = await api.get<MetricasColoquios>("/coloquios/metricas");
  return data;
}

export async function fetchConvocatorias(
  filters?: ConvocatoriasFilters,
): Promise<ConvocatoriasListResponse> {
  const params: Record<string, string> = {};
  if (filters?.materia_id) params.materia_id = filters.materia_id;
  if (filters?.cohorte_id) params.cohorte_id = filters.cohorte_id;
  if (filters?.estado) params.estado = filters.estado;
  const { data } = await api.get<ConvocatoriasListResponse>(
    "/coloquios/convocatorias",
    { params },
  );
  return data;
}

export async function crearConvocatoria(
  payload: EvaluacionCreate,
): Promise<Evaluacion> {
  const { data } = await api.post<Evaluacion>(
    "/coloquios/convocatorias",
    payload,
  );
  return data;
}

export async function fetchConvocatoriaById(
  id: string,
): Promise<Evaluacion> {
  const { data } = await api.get<Evaluacion>(`/coloquios/convocatorias/${id}`);
  return data;
}

export async function actualizarConvocatoria(
  id: string,
  payload: EvaluacionUpdate,
): Promise<Evaluacion> {
  const { data } = await api.patch<Evaluacion>(
    `/coloquios/convocatorias/${id}`,
    payload,
  );
  return data;
}

export async function cerrarConvocatoria(
  evaluacionId: string,
): Promise<void> {
  await api.post(`/coloquios/convocatorias/${evaluacionId}/cerrar`);
}

export async function importarAlumnos(
  evaluacionId: string,
  payload: ImportarAlumnosRequest,
): Promise<void> {
  await api.post(
    `/coloquios/convocatorias/${evaluacionId}/importar-alumnos`,
    payload,
  );
}

export async function fetchAgenda(
  evaluacionId?: string,
): Promise<AgendaItem[]> {
  const params: Record<string, string> = {};
  if (evaluacionId) params.evaluacion_id = evaluacionId;
  const { data } = await api.get<{ items: AgendaItem[]; total: number }>(
    "/coloquios/agenda",
    { params },
  );
  return data.items;
}
