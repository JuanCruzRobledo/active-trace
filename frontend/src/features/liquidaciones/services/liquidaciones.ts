import { api } from "@/shared/services/api";
import type {
  Liquidacion,
  LiquidacionList,
  CalcularLiquidacion,
  SalarioBase,
  SalarioBaseCreate,
  SalarioPlus,
  SalarioPlusCreate,
  ClavePlus,
  ClavePlusCreate,
  Factura,
  FacturaCreate,
  LiquidacionesFilters,
  FacturasFilters,
} from "@/features/liquidaciones/types/liquidaciones";

// ─── Liquidaciones ────────────────────────────────────────────────────────────

export async function calcularLiquidacion(
  payload: CalcularLiquidacion,
): Promise<Liquidacion> {
  const { data } = await api.post<Liquidacion>(
    "/liquidaciones/calcular",
    payload,
  );
  return data;
}

export async function fetchLiquidaciones(
  filters?: LiquidacionesFilters,
): Promise<LiquidacionList> {
  const params: Record<string, string> = {};
  if (filters?.periodo) params.periodo = filters.periodo;
  const { data } = await api.get<LiquidacionList>("/liquidaciones", { params });
  return data;
}

export async function fetchLiquidacionById(id: string): Promise<Liquidacion> {
  const { data } = await api.get<Liquidacion>(`/liquidaciones/${id}`);
  return data;
}

export async function cerrarLiquidacion(id: string): Promise<Liquidacion> {
  const { data } = await api.post<Liquidacion>(`/liquidaciones/${id}/cerrar`);
  return data;
}

// ─── Grilla — Claves Plus ─────────────────────────────────────────────────────

export async function fetchClavesPlusByActive(activas?: boolean): Promise<ClavePlus[]> {
  const params: Record<string, string> = {};
  if (activas !== undefined) params.activas = String(activas);
  const { data } = await api.get<ClavePlus[]>(
    "/liquidaciones/grilla/claves-plus",
    { params },
  );
  return data;
}

export async function crearClavePlus(payload: ClavePlusCreate): Promise<ClavePlus> {
  const { data } = await api.post<ClavePlus>(
    "/liquidaciones/grilla/claves-plus",
    payload,
  );
  return data;
}

export async function actualizarClavePlus(
  id: string,
  payload: Partial<ClavePlusCreate>,
): Promise<ClavePlus> {
  const { data } = await api.patch<ClavePlus>(
    `/liquidaciones/grilla/claves-plus/${id}`,
    payload,
  );
  return data;
}

// ─── Grilla — Salarios Base ───────────────────────────────────────────────────

export async function fetchSalariosBase(rol?: string): Promise<SalarioBase[]> {
  const params: Record<string, string> = {};
  if (rol) params.rol = rol;
  const { data } = await api.get<SalarioBase[]>(
    "/liquidaciones/grilla/salarios-base",
    { params },
  );
  return data;
}

export async function crearSalarioBase(
  payload: SalarioBaseCreate,
): Promise<SalarioBase> {
  const { data } = await api.post<SalarioBase>(
    "/liquidaciones/grilla/salarios-base",
    payload,
  );
  return data;
}

// ─── Grilla — Salarios Plus ───────────────────────────────────────────────────

export async function fetchSalariosPlus(grupo?: string): Promise<SalarioPlus[]> {
  const params: Record<string, string> = {};
  if (grupo) params.grupo = grupo;
  const { data } = await api.get<SalarioPlus[]>(
    "/liquidaciones/grilla/salarios-plus",
    { params },
  );
  return data;
}

export async function crearSalarioPlus(
  payload: SalarioPlusCreate,
): Promise<SalarioPlus> {
  const { data } = await api.post<SalarioPlus>(
    "/liquidaciones/grilla/salarios-plus",
    payload,
  );
  return data;
}

// ─── Facturas ─────────────────────────────────────────────────────────────────

export async function fetchFacturas(
  filters?: FacturasFilters,
): Promise<Factura[]> {
  const params: Record<string, string> = {};
  if (filters?.pendientes !== undefined)
    params.pendientes = String(filters.pendientes);
  if (filters?.usuario_id) params.usuario_id = filters.usuario_id;
  const { data } = await api.get<Factura[]>("/liquidaciones/facturas", {
    params,
  });
  return data;
}

export async function crearFactura(payload: FacturaCreate): Promise<Factura> {
  const { data } = await api.post<Factura>(
    "/liquidaciones/facturas",
    payload,
  );
  return data;
}

export async function abonarFactura(id: string): Promise<Factura> {
  const { data } = await api.post<Factura>(
    `/liquidaciones/facturas/${id}/abonar`,
  );
  return data;
}
