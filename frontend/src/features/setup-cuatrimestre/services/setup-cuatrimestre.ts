import { api } from "@/shared/services/api";

export interface CohorteInput {
  nombre: string;
  anio: number;
  fecha_inicio: string;
  fecha_fin: string;
  carrera_id: string;
}

/** Crea una cohorte (paso 1 del wizard) */
export async function crearCohorte(input: CohorteInput): Promise<{ id: string }> {
  const { data } = await api.post<{ id: string }>("/cohortes", input);
  return data;
}

/** Clona un equipo completo (paso 2) */
export async function clonarEquipo(origen_cohorte_id: string, destino_cohorte_id: string): Promise<void> {
  await api.post("/equipos/clonar", {
    origen_cohorte_id,
    destino_cohorte_id,
  });
}
