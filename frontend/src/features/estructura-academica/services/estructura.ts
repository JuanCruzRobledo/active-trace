import { api } from "@/shared/services/api";
import type {
  Carrera,
  CarreraCreate,
  CarreraUpdate,
  Cohorte,
  CohorteCreate,
  CohorteUpdate,
  Materia,
  MateriaCreate,
  MateriaUpdate,
} from "@/features/estructura-academica/types/estructura";

// ─── Carreras ─────────────────────────────────────────────────────────────────

export async function fetchCarreras(): Promise<Carrera[]> {
  const { data } = await api.get<Carrera[]>("/admin/carreras");
  return data;
}

export async function fetchCarreraById(id: string): Promise<Carrera> {
  const { data } = await api.get<Carrera>(`/admin/carreras/${id}`);
  return data;
}

export async function crearCarrera(payload: CarreraCreate): Promise<Carrera> {
  const { data } = await api.post<Carrera>("/admin/carreras", payload);
  return data;
}

export async function actualizarCarrera(
  id: string,
  payload: CarreraUpdate,
): Promise<Carrera> {
  const { data } = await api.patch<Carrera>(`/admin/carreras/${id}`, payload);
  return data;
}

// ─── Cohortes ─────────────────────────────────────────────────────────────────

export async function fetchCohortes(): Promise<Cohorte[]> {
  const { data } = await api.get<Cohorte[]>("/admin/cohortes");
  return data;
}

export async function fetchCohorteById(id: string): Promise<Cohorte> {
  const { data } = await api.get<Cohorte>(`/admin/cohortes/${id}`);
  return data;
}

export async function crearCohorte(payload: CohorteCreate): Promise<Cohorte> {
  const { data } = await api.post<Cohorte>("/admin/cohortes", payload);
  return data;
}

export async function actualizarCohorte(
  id: string,
  payload: CohorteUpdate,
): Promise<Cohorte> {
  const { data } = await api.patch<Cohorte>(`/admin/cohortes/${id}`, payload);
  return data;
}

// ─── Materias ─────────────────────────────────────────────────────────────────

export async function fetchMaterias(): Promise<Materia[]> {
  const { data } = await api.get<Materia[]>("/admin/materias");
  return data;
}

export async function fetchMateriaById(id: string): Promise<Materia> {
  const { data } = await api.get<Materia>(`/admin/materias/${id}`);
  return data;
}

export async function crearMateria(payload: MateriaCreate): Promise<Materia> {
  const { data } = await api.post<Materia>("/admin/materias", payload);
  return data;
}

export async function actualizarMateria(
  id: string,
  payload: MateriaUpdate,
): Promise<Materia> {
  const { data } = await api.patch<Materia>(`/admin/materias/${id}`, payload);
  return data;
}
