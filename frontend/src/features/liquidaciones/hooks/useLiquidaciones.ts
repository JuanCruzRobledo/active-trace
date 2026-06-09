import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  calcularLiquidacion,
  fetchLiquidaciones,
  fetchLiquidacionById,
  cerrarLiquidacion,
  fetchClavesPlusByActive,
  crearClavePlus,
  actualizarClavePlus,
  fetchSalariosBase,
  crearSalarioBase,
  fetchSalariosPlus,
  crearSalarioPlus,
  fetchFacturas,
  crearFactura,
  abonarFactura,
} from "@/features/liquidaciones/services/liquidaciones";
import type {
  CalcularLiquidacion,
  ClavePlusCreate,
  SalarioBaseCreate,
  SalarioPlusCreate,
  FacturaCreate,
  LiquidacionesFilters,
  FacturasFilters,
} from "@/features/liquidaciones/types/liquidaciones";

// ─── Liquidaciones ────────────────────────────────────────────────────────────

export function useLiquidaciones(filters?: LiquidacionesFilters) {
  return useQuery({
    queryKey: ["liquidaciones", filters],
    queryFn: () => fetchLiquidaciones(filters),
  });
}

export function useLiquidacionById(id: string | undefined) {
  return useQuery({
    queryKey: ["liquidaciones", id],
    queryFn: () => fetchLiquidacionById(id!),
    enabled: !!id,
  });
}

export function useCalcularLiquidacion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CalcularLiquidacion) => calcularLiquidacion(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["liquidaciones"] });
    },
  });
}

export function useCerrarLiquidacion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => cerrarLiquidacion(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["liquidaciones"] });
    },
  });
}

// ─── Grilla — Claves Plus ─────────────────────────────────────────────────────

export function useClavesPlusByActive(activas?: boolean) {
  return useQuery({
    queryKey: ["claves-plus", { activas }],
    queryFn: () => fetchClavesPlusByActive(activas),
  });
}

export function useCrearClavePlus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ClavePlusCreate) => crearClavePlus(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["claves-plus"] });
    },
  });
}

export function useActualizarClavePlus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: Partial<ClavePlusCreate>;
    }) => actualizarClavePlus(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["claves-plus"] });
    },
  });
}

// ─── Grilla — Salarios Base ───────────────────────────────────────────────────

export function useSalariosBase(rol?: string) {
  return useQuery({
    queryKey: ["salarios-base", { rol }],
    queryFn: () => fetchSalariosBase(rol),
  });
}

export function useCrearSalarioBase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SalarioBaseCreate) => crearSalarioBase(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["salarios-base"] });
    },
  });
}

// ─── Grilla — Salarios Plus ───────────────────────────────────────────────────

export function useSalariosPlus(grupo?: string) {
  return useQuery({
    queryKey: ["salarios-plus", { grupo }],
    queryFn: () => fetchSalariosPlus(grupo),
  });
}

export function useCrearSalarioPlus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SalarioPlusCreate) => crearSalarioPlus(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["salarios-plus"] });
    },
  });
}

// ─── Facturas ─────────────────────────────────────────────────────────────────

export function useFacturas(filters?: FacturasFilters) {
  return useQuery({
    queryKey: ["facturas", filters],
    queryFn: () => fetchFacturas(filters),
  });
}

export function useCrearFactura() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: FacturaCreate) => crearFactura(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["facturas"] });
    },
  });
}

export function useAbonarFactura() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => abonarFactura(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["facturas"] });
      queryClient.invalidateQueries({ queryKey: ["liquidaciones"] });
    },
  });
}
