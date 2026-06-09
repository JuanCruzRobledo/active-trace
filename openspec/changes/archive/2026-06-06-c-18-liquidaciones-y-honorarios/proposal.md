# Proposal: c-18-liquidaciones-y-honorarios

## Why

El sistema necesita gestionar la liquidación mensual de honorarios del equipo docente con trazabilidad completa, pero actualmente no existe ningún módulo que modele salarios, plus por materia, liquidaciones ni facturas. Sin esto, el área de FINANZAS no puede operar los pagos mensuales ni cerrar períodos contables dentro de la plataforma.

## What Changes

- Nuevo modelo de **grilla salarial** con `SalarioBase` (monto por rol con vigencia temporal) y `SalarioPlus` (adicional por clave de materia × rol con vigencia)
- Nuevo catálogo `ClavePlus` configurable por tenant para agrupar materias por categoría (PROG, BD, MAT, etc.), cada materia se asocia opcionalmente a una clave mediante `clave_plus_id`
- Nuevo modelo de **Liquidación** con cálculo automático (Base + Σ Plus × comisiones activas), estados Abierta/Cerrada, inmutabilidad al cerrar, y segmentación contable NEXO / facturantes / general
- Nuevo modelo de **Factura** para docentes que facturan (modalidad monotributo), con flujo Pendiente → Abonada, excluidos de liquidación general
- Endpoints REST para operar la grilla salarial (F10.4), liquidaciones (F10.1–F10.3), y facturas (F10.5) con permisos finos `liquidaciones:*`
- Migración Alembic para tablas: `clave_plus`, `salario_base`, `salario_plus`, `liquidacion`, `factura`

## Capabilities

### New Capabilities

- `grilla-salarial`: ABM de SalarioBase y SalarioPlus con vigencia temporal (`desde`/`hasta`), por rol y por clave de materia. Vista de grilla completa (F10.4).
- `clave-plus-catalogo`: Catálogo de claves de plus configurable por tenant. Cada materia se asocia a una clave mediante `clave_plus_id` (nullable).
- `liquidacion-honorarios`: Cálculo automático + vista previa + exportación + cierre con inmutabilidad + historial. Segmentación NEXO / facturantes / general con KPIs (F10.1, F10.2, F10.3, F10.6).
- `facturas-docentes`: ABM de facturas de docentes facturantes con estados Pendiente/Abonada, archivo adjunto y flujo separado de liquidación general (F10.5).

### Modified Capabilities

- *(ninguna — es un módulo completamente nuevo)*

## Impact

- **Backend**: Modelos, schemas Pydantic, repositorios, service, routers nuevos en `backend/app/models/`, `backend/app/schemas/`, `backend/app/repositories/`, `backend/app/services/`, `backend/app/routers/`
- **DB**: Nueva migración Alembic con 5 tablas (`clave_plus`, `salario_base`, `salario_plus`, `liquidacion`, `factura`)
- **Auth**: Nuevos permisos `liquidaciones:calcular`, `liquidaciones:ver`, `liquidaciones:cerrar`, `liquidaciones:exportar`, `liquidaciones:configurar-salarios`, `facturas:gestionar`
- **Riesgos**: Cálculo incorrecto del plus (validar con tests la acumulación N × plus por materia). Bloqueante: PA-22 y PA-23 ya cerradas en KB.
