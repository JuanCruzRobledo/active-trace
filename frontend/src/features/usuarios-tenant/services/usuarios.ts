import { api } from "@/shared/services/api";
import type {
  Usuario,
  UsuarioCreate,
  UsuarioUpdate,
} from "@/features/usuarios-tenant/types/usuarios";

export async function fetchUsuarios(): Promise<Usuario[]> {
  const { data } = await api.get<Usuario[]>("/admin/usuarios");
  return data;
}

export async function fetchUsuarioById(id: string): Promise<Usuario> {
  const { data } = await api.get<Usuario>(`/admin/usuarios/${id}`);
  return data;
}

export async function crearUsuario(payload: UsuarioCreate): Promise<Usuario> {
  const { data } = await api.post<Usuario>("/admin/usuarios", payload);
  return data;
}

export async function actualizarUsuario(
  id: string,
  payload: UsuarioUpdate,
): Promise<Usuario> {
  const { data } = await api.patch<Usuario>(`/admin/usuarios/${id}`, payload);
  return data;
}

export async function eliminarUsuario(id: string): Promise<void> {
  await api.delete(`/admin/usuarios/${id}`);
}
