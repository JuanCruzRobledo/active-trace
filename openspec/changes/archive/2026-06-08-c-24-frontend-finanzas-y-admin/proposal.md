# Proposal: c-24-frontend-finanzas-y-admin

## Why

El backend de **finanzas** (liquidaciones, grilla salarial, facturas — C-18), **auditoría y métricas** (C-19), **estructura académica** (carreras, cohortes, materias — C-06) y **usuarios del tenant** (C-07) está completamente implementado, pero no existe interfaz frontend para los roles FINANZAS y ADMIN. Sin este frontend, el equipo de finanzas no puede calcular ni cerrar liquidaciones, gestionar la grilla salarial ni administrar facturas; y el ADMIN no puede gestionar la estructura académica, los usuarios del tenant ni supervisar la auditoría del sistema.

Este change completa el frontend del producto (último de la serie C-21 → C-24), cerrando los módulos de finanzas y administración.

## What Changes

Implementar los módulos frontend para **finanzas** y **administración**, reutilizando la arquitectura feature-based ya establecida en C-22/C-23: TanStack Query para data fetching, React Hook Form + Zod para formularios, Tailwind CSS para estilos, y los shared components ya existentes (`FilterableTable`, `ContextoAcademicoSelector`, `ConfirmDialog`, `FormField`, etc.). Cada módulo es un feature module independiente dentro de `frontend/src/features/`.

El change es **puro frontend** — consume endpoints ya existentes en el backend; no se tocan modelos, servicios, repositorios ni routers.

## Alcance

- [ ] Incluir:
  - **Módulo `liquidaciones`** (FINANZAS, ADMIN):
    - Vista de liquidaciones del período con **segmentación contable** (general / NEXO / docentes que facturan) y KPIs de cabecera ("Total sin factura" / "Total con factura") — F10.1, F10.6
    - Filtros por cohorte, mes y docente específico
    - Vista previa del detalle individual por docente
    - **Cerrar liquidación** (inmutabilización) con confirmación — F10.2
    - **Historial** de liquidaciones cerradas — F10.3
    - **ABM de grilla salarial**: salarios base por rol con vigencia + plus (claves) por rol/clave con vigencia — F10.4
    - **Gestión de facturas** de docentes que facturan: listado filtrable, cambio de estado pendiente ↔ abonada — F10.5
  - **Módulo `estructura-academica`** (ADMIN):
    - ABM de carreras (código, nombre, estado) — F5.1
    - ABM de cohortes (nombre, año, vigencia, estado) — F5.2
    - ABM de materias — parte de F5.x estructura académica
  - **Módulo `usuarios-tenant`** (ADMIN):
    - Listado filtrable de usuarios del tenant
    - Alta, edición, activación/desactivación de usuarios con rol y datos fiscales/bancarios — F4.1
  - **Módulo `auditoria`** (ADMIN, COORDINADOR con `auditoria:ver`):
    - Panel de interacciones: acciones por día, comunicaciones por docente, interacciones por docente×materia, últimas acciones — F9.1
    - Filtros: rango de fechas, materia, usuario, estado de actividad
    - Log completo de auditoría con todos los campos — F9.2
  - Navegación: secciones "Finanzas" y "Administración" en el menú, visibles según permisos del usuario
  - Rutas protegidas con `<RequirePermission>` por permiso correspondiente
- [ ] Excluir:
  - Backend: no se tocan modelos, servicios, repositorios ni endpoints existentes
  - Módulos ya cubiertos por C-22 (académico/docente) y C-23 (coordinación)
  - Cualquier cambio en el shell o auth (C-21)

## Impacto

- **Frontend**: 4 nuevos feature modules (`liquidaciones`, `estructura-academica`, `usuarios-tenant`, `auditoria`) + entradas de navegación nuevas
- **Backend**: Sin cambios — todos los endpoints ya existen (C-06, C-07, C-18, C-19)
- **Governance**: BAJO — frontend que consume endpoints existentes; el backend de finanzas (CRÍTICO) ya está implementado y archivado
- **Riesgo**: Los schemas de respuesta del frontend deben coincidir con lo que devuelven realmente los endpoints
  - **Mitigación**: Validar los DTOs de respuesta contra los schemas Pydantic de los routers durante apply; cualquier discrepancia se resuelve en esa fase
