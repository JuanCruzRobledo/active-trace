import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getComunicaciones,
  getAlumnosAtrasadosParaComunicacion,
  crearComunicacion,
  getComunicacion,
  type ComunicacionesResponse,
  type AlumnoAtrasadoOption,
  type CrearComunicacionRequest,
  type CrearComunicacionResponse,
  type ComunicacionItem,
} from "@/features/comision/services/comunicaciones";

export function useComunicaciones() {
  return useQuery<ComunicacionesResponse>({
    queryKey: ["comunicaciones"],
    queryFn: () => getComunicaciones(),
  });
}

export function useAlumnosAtrasadosParaComunicacion(materiaId: string) {
  return useQuery<AlumnoAtrasadoOption[]>({
    queryKey: ["comunicaciones-destinatarios", materiaId],
    queryFn: () => getAlumnosAtrasadosParaComunicacion(materiaId),
    enabled: !!materiaId,
  });
}

export function useCrearComunicacion() {
  const queryClient = useQueryClient();
  return useMutation<
    CrearComunicacionResponse,
    Error,
    CrearComunicacionRequest
  >({
    mutationFn: (req: CrearComunicacionRequest) => crearComunicacion(req),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["comunicaciones"] });
    },
  });
}

export function useComunicacionPolling(
  comunicacionId: string | null,
  enabled: boolean,
) {
  return useQuery<ComunicacionItem>({
    queryKey: ["comunicacion", comunicacionId],
    queryFn: () => getComunicacion(comunicacionId!),
    enabled: enabled && !!comunicacionId,
    refetchInterval: (query) => {
      const estado = query.state.data?.estado;
      if (estado === "Pendiente" || estado === "En envío") return 5000;
      return false;
    },
  });
}
