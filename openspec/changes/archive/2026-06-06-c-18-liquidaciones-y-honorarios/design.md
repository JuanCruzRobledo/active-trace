# Design: c-18-liquidaciones-y-honorarios

## Context

El módulo de liquidaciones cubre la Épica 10 del producto (F10.1–F10.6). Es el módulo que permite al rol FINANZAS operar la grilla salarial, calcular liquidaciones mensuales, gestionar facturas de docentes que facturan, y cerrar períodos contables con inmutabilidad.

Actualmente el sistema no tiene ninguna entidad de salarios, liquidaciones ni facturas. Las reglas de negocio están definidas en RN-31 a RN-40 y la resolución de preguntas abiertas PA-22, PA-23 y PA-25 ya está documentada en la KB.

**Restricciones conocidas:**
- Governance: **CRÍTICO** — módulo financiero, requiere aprobación humana explícita para escribir código
- Multi-tenancy row-level: toda entidad lleva `tenant_id`
- Soft delete no aplica a liquidaciones (son inmutables al cerrar)
- Datos cifrados en reposo: CBU, alias, DNI del usuario ya existen en E4

## Goals / Non-Goals

**Goals:**
- Modelar el catálogo `ClavePlus` configurable por tenant con 8 claves default en seed
- Modelar `SalarioBase` (por rol, vigencia) y `SalarioPlus` (por clave × rol, vigencia)
- Calcular liquidación automática por (cohorte × mes): `Base(rol) + Σ(Plus(clave, rol) × N_comisiones)`
- Soportar tres segmentos contables: general (no factura), NEXO (separado pero suma), facturantes (excluidos del total)
- ABM de facturas con estados Pendiente / Abonada y archivo adjunto
- Endpoints REST con permisos finos `liquidaciones:*` y `facturas:*`
- Cobertura ≥80% líneas, ≥90% reglas de negocio, Strict TDD

**Non-Goals:**
- Integración con sistemas de pago externos (Mercado Pago, transferencias bancarias, etc.)
- Cálculo de retenciones impositivas
- Generación de recibos de sueldo digitales firmados
- Workflows de aprobación multi-paso (solo FINANZAS opera)
- Notificaciones automáticas al cerrar liquidación

## Decisions

### D1 — ClavePlus como entidad (no enum fijo)
- **Opción A** (elegida): Entidad `ClavePlus` configurable por tenant con FK desde `Materia.clave_plus_id` (nullable)
- **Opción B**: Enum fijo en código con valores PROG, BD, etc.
- **Por qué A**: Cada institución tiene su propia estructura curricular. Un tenant de medicina no comparte claves con uno de ingeniería. Además, permite que el ADMIN configure nuevas claves sin deploy.
- **Consecuencia**: Migración inicial + seed de 8 claves por defecto.

### D2 — Acumulación de Plus sin tope
- **Opción A** (elegida): `Total Plus = Σ(Plus(clave, rol) × N_comisiones_activas)` sin límite superior
- **Opción B**: Tope de 3 comisiones por clave, o tope global
- **Por qué A**: RN-33 explícitamente dice "acumula N veces" y RN-34 no menciona tope. Además, en la práctica los docentes raramente tienen más de 3-4 comisiones de la misma materia. Si en el futuro se necesita un tope, se agrega como columna `tope` en `ClavePlus`.

### D3 — Liquidación inmutable al cerrar (no soft delete)
- **Opción A** (elegida): `estado: Abierta | Cerrada`. Al cerrar, el cálculo se congela y no puede modificarse.
- **Opción B**: Borrado lógico con `deleted_at` como el resto del sistema.
- **Por qué A**: Una liquidación cerrada es un **documento contable**. Modificarlo o borrarlo rompe la auditoría. RN-22 es explícita: "inmutable". El soft delete no aplica.

### D4 — Cálculo de N_comisiones desde Asignacion
- El sistema ya tiene el modelo `Asignacion` que vincula `Usuario × Materia × Cohorte × Rol` con vigencia. Para calcular `N_comisiones`, se cuentan las asignaciones activas del docente en el período cuya materia tenga `clave_plus_id` no nulo, agrupadas por clave.
- No se crea una tabla intermedia adicional.

### D5 — Segmentación NEXO vs general desde Liquidacion
- El campo `es_nexo: boolean` en `Liquidacion` permite filtrar. Los reportes (F10.6) agrupan por este flag más `excluido_por_factura`. No se necesitan tablas separadas.

## Modelo de Datos

### Nuevas entidades

**ClavePlus (E18.5)**
```
ClavePlus {
  id          : UUID       — PK
  tenant_id   : UUID       — FK → Tenant
  codigo      : texto      — único por tenant (PROG, BD, MAT, ...)
  nombre      : texto      — nombre legible
  descripcion : texto      — opcional
  activa      : booleano   — si false, no se usa en nuevos cálculos
}
```

**Modificación a Materia (E3)**
```
+ clave_plus_id : UUID  — FK → ClavePlus (nullable; si nulo, no genera plus)
```

**SalarioBase (E17)** — sin cambios respecto a KB
**SalarioPlus (E18)** — `grupo` pasa a ser FK → `ClavePlus.codigo`
**Liquidacion (E19)** — sin cambios respecto a KB
**Factura (E20)** — sin cambios respecto a KB

### Relaciones nuevas
```
ClavePlus (1) ─── (N) Materia
ClavePlus (1) ─── (N) SalarioPlus
```

## APIs

### Grilla Salarial (F10.4)
| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| GET | `/api/v1/liquidaciones/grilla/salarios-base` | `liquidaciones:configurar-salarios` | Lista SalarioBase (vigentes o todos) |
| POST | `/api/v1/liquidaciones/grilla/salarios-base` | `liquidaciones:configurar-salarios` | Crea nuevo SalarioBase |
| PUT | `/api/v1/liquidaciones/grilla/salarios-base/{id}` | `liquidaciones:configurar-salarios` | Actualiza (cierra vigencia anterior si cambia monto) |
| GET | `/api/v1/liquidaciones/grilla/salarios-plus` | `liquidaciones:configurar-salarios` | Lista SalarioPlus |
| POST | `/api/v1/liquidaciones/grilla/salarios-plus` | `liquidaciones:configurar-salarios` | Crea nuevo SalarioPlus |
| PUT | `/api/v1/liquidaciones/grilla/salarios-plus/{id}` | `liquidaciones:configurar-salarios` | Actualiza |
| GET | `/api/v1/liquidaciones/grilla/claves-plus` | `liquidaciones:configurar-salarios` | Lista ClavePlus del tenant |
| POST | `/api/v1/liquidaciones/grilla/claves-plus` | `liquidaciones:configurar-salarios` | Crea nueva ClavePlus |

### Liquidaciones (F10.1, F10.2, F10.3, F10.6)
| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| POST | `/api/v1/liquidaciones/calcular` | `liquidaciones:calcular` | Calcula liquidaciones para (cohorte, mes). Devuelve preview. |
| GET | `/api/v1/liquidaciones` | `liquidaciones:ver` | Lista liquidaciones (filtro: cohorte, mes, docente) |
| GET | `/api/v1/liquidaciones/{id}` | `liquidaciones:ver` | Detalle de liquidación individual |
| POST | `/api/v1/liquidaciones/{id}/cerrar` | `liquidaciones:cerrar` | Cierra y inmutabiliza la liquidación |
| GET | `/api/v1/liquidaciones/exportar?cohorte=&mes=` | `liquidaciones:exportar` | Exporta planilla del período |

### Facturas (F10.5)
| Método | Ruta | Permiso | Descripción |
|--------|------|---------|-------------|
| GET | `/api/v1/facturas` | `facturas:gestionar` | Lista facturas con filtros |
| POST | `/api/v1/facturas` | `facturas:gestionar` | Registra nueva factura (con archivo adjunto) |
| PUT | `/api/v1/facturas/{id}/estado` | `facturas:gestionar` | Cambia estado Pendiente → Abonada |

## Riesgos / Trade-offs

| Riesgo | Mitigación |
|--------|-----------|
| **Cálculo incorrecto de plus**: error al contar comisiones activas por clave de materia | Tests parametrizados con múltiples combinaciones de comisiones; triangulación obligatoria |
| **Race condition al cerrar liquidación**: dos requests cierran la misma liquidación simultáneamente | Optimistic locking con `version` o `SELECT FOR UPDATE` en la transacción de cierre |
| **Archivos adjuntos de facturas sin validación de tamaño/tipo** | Validar tipo MIME (PDF, imagen) y tamaño máximo (ej: 10MB) antes de persistir |
| **Datos bancarios del docente no cifrados en respuesta** | El schema de respuesta nunca expone CBU completo solo máscara (últimos 4 dígitos) |

## Open Questions

- *(ninguna — PA-22, PA-23 y PA-25 ya están cerradas)*
