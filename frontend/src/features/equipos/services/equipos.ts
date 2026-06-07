import { api } from "@/shared/services/api";
import type {
  EquipoResponse,
  EquipoFilters,
  VigenciaResponse,
  ClonarResponse,
  AsignacionMasivaRequest,
  ClonarEquipoRequest,
  VigenciaRequest,
} from "@/features/equipos/types/equipos";

export async function fetchMisEquipos(filters?: EquipoFilters): Promise<EquipoResponse[]> {
  const { data } = await api.get<EquipoResponse[]>("/equipos/mis-equipos", { params: filters });
  return data;
}

export async function fetchAsignaciones(filters?: EquipoFilters): Promise<EquipoResponse[]> {
  const { data } = await api.get<EquipoResponse[]>("/equipos", { params: filters });
  return data;
}

export async function asignacionMasiva(req: AsignacionMasivaRequest): Promise<EquipoResponse[]> {
  const { data } = await api.post<EquipoResponse[]>("/equipos/asignacion-masiva", req);
  return data;
}

export async function clonarEquipo(req: ClonarEquipoRequest): Promise<ClonarResponse> {
  const { data } = await api.post<ClonarResponse>("/equipos/clonar", req);
  return data;
}

export async function actualizarVigencia(req: VigenciaRequest): Promise<VigenciaResponse> {
  const { data } = await api.patch<VigenciaResponse>("/equipos/vigencia", req);
  return data;
}

export async function exportarEquipo(
  materia_id: string,
  carrera_id: string,
  cohorte_id: string,
): Promise<Blob> {
  const { data } = await api.get<Blob>("/equipos/export", {
    params: { materia_id, carrera_id, cohorte_id },
    responseType: "blob",
  });
  return data;
}
