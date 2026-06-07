import { api } from "@/shared/services/api";
import type {
  Tarea,
  TareaConComentarios,
  TareaCreate,
  TareaEstadoUpdate,
  Comentario,
  ComentarioCreate,
  TareaListResponse,
  TareasFilters,
} from "@/features/tareas/types/tareas";

export async function fetchMisTareas(
  estado?: string,
  materiaId?: string,
): Promise<TareaListResponse> {
  const params: Record<string, string> = {};
  if (estado) params.estado = estado;
  if (materiaId) params.materia_id = materiaId;
  const { data } = await api.get<TareaListResponse>("/tareas/mias", { params });
  return data;
}

export async function fetchTareasAdmin(
  filters?: TareasFilters,
): Promise<TareaListResponse> {
  const params: Record<string, string> = {};
  if (filters?.estado) params.estado = filters.estado;
  if (filters?.materia_id) params.materia_id = filters.materia_id;
  if (filters?.asignado_a) params.asignado_a = filters.asignado_a;
  if (filters?.asignado_por) params.asignado_por = filters.asignado_por;
  if (filters?.busqueda) params.busqueda = filters.busqueda;
  const { data } = await api.get<TareaListResponse>("/tareas", { params });
  return data;
}

export async function fetchTareaById(id: string): Promise<TareaConComentarios> {
  const { data } = await api.get<TareaConComentarios>(`/tareas/${id}`);
  return data;
}

export async function crearTarea(payload: TareaCreate): Promise<Tarea> {
  const { data } = await api.post<Tarea>("/tareas", payload);
  return data;
}

export async function actualizarEstadoTarea(
  id: string,
  payload: TareaEstadoUpdate,
): Promise<void> {
  await api.patch(`/tareas/${id}/estado`, payload);
}

export async function agregarComentario(
  tareaId: string,
  payload: ComentarioCreate,
): Promise<Comentario> {
  const { data } = await api.post<Comentario>(
    `/tareas/${tareaId}/comentarios`,
    payload,
  );
  return data;
}
