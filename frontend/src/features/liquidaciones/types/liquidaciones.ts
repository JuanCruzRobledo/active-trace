import { z } from "zod";

// ─── Enums ────────────────────────────────────────────────────────────────────

export const LiquidacionEstadoEnum = z.enum(["abierta", "cerrada"]);
export const FacturaEstadoEnum = z.enum(["pendiente", "abonada"]);

// ─── Liquidación ──────────────────────────────────────────────────────────────

export const LiquidacionSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  cohorte_id: z.string().uuid(),
  periodo: z.string(), // YYYY-MM
  usuario_id: z.string().uuid(),
  rol: z.string(),
  comisiones: z.number().int(),
  monto_base: z.string(),
  monto_plus: z.string(),
  total: z.string(),
  es_nexo: z.boolean(),
  excluido_por_factura: z.boolean(),
  estado: LiquidacionEstadoEnum,
  cerrada_at: z.string().nullable().optional(),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
}).passthrough();

export type Liquidacion = z.infer<typeof LiquidacionSchema>;

export const LiquidacionListSchema = z.array(LiquidacionSchema);
export type LiquidacionList = z.infer<typeof LiquidacionListSchema>;

// ─── Calcular payload ─────────────────────────────────────────────────────────

export const CalcularLiquidacionSchema = z.object({
  cohorte_id: z.string().uuid("Seleccioná una cohorte"),
  periodo: z.string().regex(/^\d{4}-\d{2}$/, "Formato YYYY-MM"),
  usuario_id: z.string().uuid("Seleccioná un usuario"),
  rol: z.string().min(1, "El rol es obligatorio"),
  comisiones: z.number().int().min(0),
}).strict();

export type CalcularLiquidacion = z.infer<typeof CalcularLiquidacionSchema>;

// ─── Segmentos ────────────────────────────────────────────────────────────────

export interface SegmentosLiquidacion {
  general: Liquidacion[];
  nexo: Liquidacion[];
  facturan: Liquidacion[];
}

export interface KpisLiquidacion {
  totalGeneral: number;
  totalNexo: number;
  totalFacturan: number; // informational only, not summed
  totalSinFactura: number; // general + nexo
}

// ─── Grilla Salarial ──────────────────────────────────────────────────────────

export const SalarioBaseSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  rol: z.string(),
  monto: z.string(),
  desde: z.string().nullable().optional(),
  hasta: z.string().nullable().optional(),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
}).passthrough();

export type SalarioBase = z.infer<typeof SalarioBaseSchema>;

export const SalarioBaseCreateSchema = z.object({
  rol: z.string().min(1, "El rol es obligatorio"),
  monto: z.string().min(1, "El monto es obligatorio"),
  desde: z.string().optional(),
  hasta: z.string().optional(),
}).strict();

export type SalarioBaseCreate = z.infer<typeof SalarioBaseCreateSchema>;

export const SalarioPlusSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  grupo: z.string(),
  rol: z.string(),
  descripcion: z.string(),
  monto: z.string(),
  desde: z.string().nullable().optional(),
  hasta: z.string().nullable().optional(),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
}).passthrough();

export type SalarioPlus = z.infer<typeof SalarioPlusSchema>;

export const SalarioPlusCreateSchema = z.object({
  grupo: z.string().min(1, "El grupo es obligatorio"),
  rol: z.string().min(1, "El rol es obligatorio"),
  descripcion: z.string().min(1, "La descripción es obligatoria"),
  monto: z.string().min(1, "El monto es obligatorio"),
  desde: z.string().optional(),
  hasta: z.string().optional(),
}).strict();

export type SalarioPlusCreate = z.infer<typeof SalarioPlusCreateSchema>;

export const ClavePlusSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  codigo: z.string(),
  nombre: z.string(),
  activa: z.boolean(),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
}).passthrough();

export type ClavePlus = z.infer<typeof ClavePlusSchema>;

export const ClavePlusCreateSchema = z.object({
  codigo: z.string().min(1, "El código es obligatorio"),
  nombre: z.string().min(1, "El nombre es obligatorio"),
  activa: z.boolean().default(true),
}).strict();

export type ClavePlusCreate = z.infer<typeof ClavePlusCreateSchema>;

// ─── Facturas ─────────────────────────────────────────────────────────────────

export const FacturaSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  usuario_id: z.string().uuid(),
  periodo: z.string(),
  detalle: z.string().nullable().optional(),
  referencia_archivo: z.string().nullable().optional(),
  tamano_kb: z.number().nullable().optional(),
  estado: FacturaEstadoEnum,
  cargada_at: z.string().nullable().optional(),
  abonada_at: z.string().nullable().optional(),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
}).passthrough();

export type Factura = z.infer<typeof FacturaSchema>;

export const FacturaCreateSchema = z.object({
  usuario_id: z.string().uuid("Seleccioná un usuario"),
  periodo: z.string().regex(/^\d{4}-\d{2}$/, "Formato YYYY-MM"),
  detalle: z.string().optional(),
  referencia_archivo: z.string().optional(),
  tamano_kb: z.number().optional(),
}).strict();

export type FacturaCreate = z.infer<typeof FacturaCreateSchema>;

// ─── Filtros ──────────────────────────────────────────────────────────────────

export interface LiquidacionesFilters {
  periodo?: string;
  cohorte_id?: string;
  usuario_id?: string;
  rol?: string;
}

export interface FacturasFilters {
  pendientes?: boolean;
  usuario_id?: string;
  periodo?: string;
  estado?: string;
}
