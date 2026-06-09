import { api } from "@/shared/services/api";

export type ComunicacionEstado =
  | "Pendiente"
  | "En envío"
  | "Enviado"
  | "Fallido"
  | "Cancelado";

export interface ComunicacionItem {
  id: string;
  asunto: string;
  estado: ComunicacionEstado;
  total_destinatarios: number;
  enviados: number;
  fallidos: number;
  created_at: string;
  materia_id: string;
}

export interface ComunicacionesResponse {
  items: ComunicacionItem[];
  total: number;
}

export interface AlumnoAtrasadoOption {
  alumno_id: string;
  alumno: string;
  legajo: string;
  seleccionado: boolean;
}

export interface CrearComunicacionRequest {
  materia_id: string;
  asunto: string;
  cuerpo: string;
  destinatarios: string[];
}

export interface CrearComunicacionResponse {
  id: string;
  estado: ComunicacionEstado;
}

export async function getComunicaciones(): Promise<ComunicacionesResponse> {
  const { data } = await api.get<ComunicacionesResponse>(
    `/comunicaciones/mis-envios`,
  );
  return data;
}

/** @deprecated No existe endpoint directo en backend. Usar preview + enviar. */
export async function getAlumnosAtrasadosParaComunicacion(
  _materiaId: string,
): Promise<AlumnoAtrasadoOption[]> {
  console.warn("getAlumnosAtrasadosParaComunicacion no implementado en backend");
  return [];
}

export async function crearComunicacion(
  req: CrearComunicacionRequest,
): Promise<CrearComunicacionResponse> {
  const { data } = await api.post<CrearComunicacionResponse>(
    `/comunicaciones/enviar`,
    { ...req, acepta_terminos: true, requiere_aprobacion: false },
  );
  return data;
}

export async function getComunicacion(
  loteId: string,
): Promise<ComunicacionItem> {
  const { data } = await api.get<ComunicacionItem>(
    `/comunicaciones/${loteId}`,
  );
  return data;
}
