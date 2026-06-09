# Tasks: c-18-liquidaciones-y-honorarios

## Implementation Checklist

### 1. Modelos y Migración

- [ ] 1.1 Crear modelo `ClavePlus` con campos: id, tenant_id, codigo, nombre, descripcion, activa. Unique `(tenant_id, codigo)`. FK → Tenant.
- [ ] 1.2 Agregar campo `clave_plus_id` (UUID, nullable, FK → ClavePlus) al modelo `Materia` existente.
- [ ] 1.3 Crear modelo `SalarioBase` con campos: id, tenant_id, rol (enum), monto, desde, hasta (nullable). Unique constraint por tenant + rol + período de vigencia.
- [ ] 1.4 Crear modelo `SalarioPlus` con campos: id, tenant_id, grupo (FK → ClavePlus.codigo), rol (enum), descripcion, monto, desde, hasta (nullable).
- [ ] 1.5 Crear modelo `Liquidacion` con campos: id, tenant_id, cohorte_id (FK), periodo (AAAA-MM), usuario_id (FK), rol, comisiones (lista texto), monto_base, monto_plus, total, es_nexo, excluido_por_factura, estado (Abierta/Cerrada).
- [ ] 1.6 Crear modelo `Factura` con campos: id, tenant_id, usuario_id (FK), periodo, detalle, referencia_archivo, tamano_kb, estado (Pendiente/Abonada), cargada_at, abonada_at (nullable).
- [ ] 1.7 Agregar a `enums.py` los enums: `EstadoLiquidacion` (Abierta, Cerrada), `EstadoFactura` (Pendiente, Abonada).
- [ ] 1.8 Agregar a `enums.py` los códigos de auditoría: `LIQUIDACION_CERRAR`, `FACTURA_ABONAR`.
- [ ] 1.9 Crear migración Alembic 0NN con tablas: `clave_plus`, `salario_base`, `salario_plus`, `liquidacion`, `factura` + alter table `materia` add `clave_plus_id` + índices FK y unique constraints.
- [ ] 1.10 Agregar seed de 8 claves por defecto: PROG, BD, ING, MAT, RED, WEB, GES, IDI, PRA.
- [ ] 1.11 Agregar relaciones SQLAlchemy: ClavePlus ↔ Materia/SalarioPlus, Liquidacion ↔ Cohorte/Usuario, Factura ↔ Usuario.
- [ ] 1.12 Registrar modelos en `backend/app/models/__init__.py`.

### 2. Pydantic Schemas

- [ ] 2.1 Crear schemas `ClavePlusCreate`, `ClavePlusUpdate`, `ClavePlusResponse`, `ClavePlusListResponse`.
- [ ] 2.2 Crear schemas `SalarioBaseCreate`, `SalarioBaseUpdate`, `SalarioBaseResponse`, `SalarioBaseListResponse`.
- [ ] 2.3 Crear schemas `SalarioPlusCreate`, `SalarioPlusUpdate`, `SalarioPlusResponse`, `SalarioPlusListResponse`.
- [ ] 2.4 Crear schemas `LiquidacionResponse`, `LiquidacionListResponse`, `LiquidacionCalcularRequest` (cohorte_id, periodo), `LiquidacionCerrarResponse`.
- [ ] 2.5 Crear schemas `FacturaCreate` (usuario_id, periodo, detalle, archivo opcional), `FacturaUpdateEstado`, `FacturaResponse`, `FacturaListResponse`.
- [ ] 2.6 Crear schema `VistaPreviaResponse` con items (liquidaciones) + kpis (total_sin_factura, total_con_factura).
- [ ] 2.7 Agregar `ConfigDict(extra='forbid')` en todos los schemas.

### 3. Repository Layer

- [ ] 3.1 Implementar `ClavePlusRepository` con métodos: create, list (activas/todas), get_by_codigo, update, soft-disable.
- [ ] 3.2 Implementar `SalarioBaseRepository` con métodos: create, get_vigente(rol, fecha), list (con filtro por período), update (cerrar vigencia anterior + crear nueva), get_by_id.
- [ ] 3.3 Implementar `SalarioPlusRepository` con métodos: create, get_vigentes(rol, fecha), get_by_clave_rol(clave, rol, fecha), list (con filtros), update.
- [ ] 3.4 Implementar `LiquidacionRepository` con métodos: create (batch), get_by_id, list (filtros cohorte/período/docente), update_estado (con verificación de estado anterior Abierta para evitar doble cierre), get_by_cohorte_periodo.
- [ ] 3.5 Implementar `FacturaRepository` con métodos: create, get_by_id, list (filtros docente/estado/rango fechas/búsqueda), update_estado.
- [ ] 3.6 Implementar tenant scope obligatorio en todos los repositorios.

### 4. Service Layer

- [ ] 4.1 Implementar `GrillaSalarialService.configurar_base` — crear/actualizar SalarioBase cerrando vigencia anterior si cambia monto.
- [ ] 4.2 Implementar `GrillaSalarialService.listar_grilla_completa` — retorna SalarioBase + SalarioPlus vigentes o por filtro.
- [ ] 4.3 Implementar `LiquidacionService.calcular` — lógica central: por cada docente con asignaciones activas en (cohorte, período), calcular base + plus, crear Liquidacion con segmentación (es_nexo, excluido_por_factura). Retorna preview.
- [ ] 4.4 Implementar `LiquidacionService.vista_previa` — recalcular y mostrar preview con KPIs de cabecera.
- [ ] 4.5 Implementar `LiquidacionService.cerrar` — validar estado Abierta, cambiar a Cerrada, registrar audit `LIQUIDACION_CERRAR`, usar optimistic locking o SELECT FOR UPDATE.
- [ ] 4.6 Implementar `LiquidacionService.exportar` — generar CSV/Excel del período.
- [ ] 4.7 Implementar `LiquidacionService.listar_historial` — con filtros, solo lectura.
- [ ] 4.8 Implementar `FacturaService.registrar` — validar que usuario tenga facturador=true, crear factura en estado Pendiente.
- [ ] 4.9 Implementar `FacturaService.cambiar_estado` — validar transición Pendiente→Abonada, registrar audit.

### 5. API Endpoints

- [ ] 5.1 Crear router `grilla_salarial_router.py`:
  - GET `/api/v1/liquidaciones/grilla/salarios-base`
  - POST `/api/v1/liquidaciones/grilla/salarios-base`
  - PUT `/api/v1/liquidaciones/grilla/salarios-base/{id}`
  - GET `/api/v1/liquidaciones/grilla/salarios-plus`
  - POST `/api/v1/liquidaciones/grilla/salarios-plus`
  - PUT `/api/v1/liquidaciones/grilla/salarios-plus/{id}`
  - GET `/api/v1/liquidaciones/grilla/claves-plus`
  - POST `/api/v1/liquidaciones/grilla/claves-plus`
  - Con guard `liquidaciones:configurar-salarios`
- [ ] 5.2 Crear router `liquidaciones_router.py`:
  - POST `/api/v1/liquidaciones/calcular` — guard `liquidaciones:calcular`
  - GET `/api/v1/liquidaciones` — guard `liquidaciones:ver`
  - GET `/api/v1/liquidaciones/{id}` — guard `liquidaciones:ver`
  - POST `/api/v1/liquidaciones/{id}/cerrar` — guard `liquidaciones:cerrar`
  - GET `/api/v1/liquidaciones/exportar` — guard `liquidaciones:exportar`
- [ ] 5.3 Crear router `facturas_router.py`:
  - GET `/api/v1/facturas` — guard `facturas:gestionar`
  - POST `/api/v1/facturas` — guard `facturas:gestionar`
  - PUT `/api/v1/facturas/{id}/estado` — guard `facturas:gestionar`
- [ ] 5.4 Agregar validación Pydantic en todos los endpoints.
- [ ] 5.5 Registrar routers en la app principal.
- [ ] 5.6 Agregar permisos `liquidaciones:calcular`, `liquidaciones:ver`, `liquidaciones:cerrar`, `liquidaciones:exportar`, `liquidaciones:configurar-salarios`, `facturas:gestionar` al seed de permisos.

### 6. Tests

- [ ] 6.1 Test: ClavePlus CRUD (crear, listar, desactivar, unique por tenant, seed por defecto).
- [ ] 6.2 Test: SalarioBase — crear, vigencia por período, actualizar cierra anterior, conflict si dos vigentes mismo rol.
- [ ] 6.3 Test: SalarioPlus — crear, listar por clave y rol, vigencia.
- [ ] 6.4 Test: Cálculo de liquidación — docente sin comisiones → solo base.
- [ ] 6.5 Test: Cálculo de liquidación — docente con 3 comisiones PROG → monto_plus = 3 × Plus(PROG, PROFESOR).
- [ ] 6.6 Test: Cálculo de liquidación — multi-key (2 PROG + 1 BD → suma de ambos plus).
- [ ] 6.7 Test: Cálculo de liquidación — materias sin clave_plus_id no generan plus.
- [ ] 6.8 Test: Cálculo de liquidación — docente facturador → excluido_por_factura = true, total = 0.
- [ ] 6.9 Test: Cálculo de liquidación — NEXO → es_nexo = true, base > 0, plus = 0.
- [ ] 6.10 Test: Vista previa con KPIs correctos (total sin factura, total con factura).
- [ ] 6.11 Test: Cierre de liquidación exitoso + audit log.
- [ ] 6.12 Test: Cierre de liquidación ya cerrada → 409.
- [ ] 6.13 Test: Liquidación cerrada no puede modificarse.
- [ ] 6.14 Test: Factura CRUD — crear, listar con filtros, búsqueda.
- [ ] 6.15 Test: Factura — cambiar estado Pendiente → Abonada.
- [ ] 6.16 Test: Factura — cambiar estado ya abonada → 409.
- [ ] 6.17 Test: Factura — docente no facturador → 422.
- [ ] 6.18 Test: Multi-tenancy — datos de tenant A no visibles en tenant B (grilla, liquidaciones, facturas).
- [ ] 6.19 Test: Permisos — cada endpoint retorna 403 sin el permiso correspondiente.

## Dependencias

- spec: `grilla-salarial` en `specs/grilla-salarial/spec.md`
- spec: `clave-plus-catalogo` en `specs/clave-plus-catalogo/spec.md`
- spec: `liquidacion-honorarios` en `specs/liquidacion-honorarios/spec.md`
- spec: `facturas-docentes` en `specs/facturas-docentes/spec.md`
- design: `design.md`
- Dependencias de implementación: C-07 (usuarios-y-asignaciones) — para modelo Usuario y Asignacion

## Notas de Implementación

- **Governance CRÍTICO**: todas las tasks requieren aprobación humana antes de escribir código.
- **TDD obligatorio**: test que falla → código mínimo → triangulación → refactor.
- **Multi-tenancy**: toda query debe incluir tenant scope. Nunca query sin `WHERE tenant_id = ?`.
- **Cálculo de plus**: usar RN-34: `Total = Base(rol) + Σ(Plus(clave, rol) × N_comisiones)`. No hay tope de acumulación (PA-23).
- **Cierre de liquidación**: usar `SELECT FOR UPDATE` o `version` column para evitar race conditions.
- **Facturas**: el archivo adjunto debe validarse (tipo MIME, tamaño máx 10MB). No es necesario implementar almacenamiento real en primera iteración — usar referencia a archivo local.
- **Seed de claves**: las 8 claves default se precargan al crear un tenant nuevo, no al migrar.
