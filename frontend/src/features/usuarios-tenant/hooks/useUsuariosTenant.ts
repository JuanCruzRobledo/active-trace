import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchUsuarios,
  fetchUsuarioById,
  crearUsuario,
  actualizarUsuario,
  eliminarUsuario,
} from "@/features/usuarios-tenant/services/usuarios";
import type {
  UsuarioCreate,
  UsuarioUpdate,
} from "@/features/usuarios-tenant/types/usuarios";

export function useUsuariosTenant() {
  return useQuery({
    queryKey: ["usuarios-tenant"],
    queryFn: fetchUsuarios,
  });
}

export function useUsuarioTenantById(id: string | undefined) {
  return useQuery({
    queryKey: ["usuarios-tenant", id],
    queryFn: () => fetchUsuarioById(id!),
    enabled: !!id,
  });
}

export function useCrearUsuarioTenant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: UsuarioCreate) => crearUsuario(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["usuarios-tenant"] });
    },
  });
}

export function useActualizarUsuarioTenant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UsuarioUpdate }) =>
      actualizarUsuario(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["usuarios-tenant"] });
    },
  });
}

export function useEliminarUsuarioTenant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => eliminarUsuario(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["usuarios-tenant"] });
    },
  });
}
