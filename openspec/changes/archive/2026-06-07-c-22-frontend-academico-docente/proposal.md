## Why

El backend ya expone endpoints completos para importación de calificaciones (C-10), análisis de atrasados y rankings (C-11), comunicaciones con cola y tracking (C-12), y monitores de seguimiento (C-11). Sin embargo, el frontend solo cuenta con el shell de auth y layout (C-21). Los usuarios Profesor, Tutor y Coordinador no tienen acceso visual a estas funcionalidades, lo que hace al producto inusable para su propósito principal: gestionar comisiones desde el frontend.

## What Changes

- Creación del feature module `features/comision/` con página de gestión de comisión del profesor
- Vista de importación de calificaciones con preview, selección de actividades y confirmación
- Vista de configuración de umbral de aprobación por materia
- Vista de alumnos atrasados con tabla, filtros y métricas de riesgo
- Vista de ranking de actividades aprobadas
- Vista de notas finales agrupadas y reportes rápidos
- Vista de detección y exportación de entregas sin corregir
- Vista de comunicación a atrasados con preview, envío y tracking de estado en tiempo real
- Feature module `features/monitores/` con monitor de seguimiento para tutor/profesor
- Integración con el layout existente (AppLayout), el sistema de auth (useAuth, RequirePermission) y el cliente HTTP centralizado (api.ts)
- Tests de componentes e integración con mocks de API

## Capabilities

### New Capabilities
- `comision-importacion`: Importación de calificaciones con preview y selección de actividades. Consume endpoints de calificaciones (C-10).
- `comision-umbral`: Configuración del umbral de aprobación por materia. Consume endpoints de umbral (C-11).
- `comision-atrasados`: Vista de alumnos atrasados con tabla, filtros y métricas de riesgo. Consume endpoints de análisis (C-11).
- `comision-rankings`: Ranking de actividades aprobadas y notas finales agrupadas. Consume endpoints de rankings/reportes (C-11).
- `comision-reportes`: Reportes rápidos por materia y exportación de entregas sin corregir. Consume endpoints de análisis (C-11).
- `comision-comunicaciones`: Preview de comunicación masiva, envío con cola y tracking de estado en tiempo real. Consume endpoints de comunicaciones (C-12).
- `monitores-seguimiento-frontend`: Monitor de seguimiento de alumnos para tutor/profesor con filtros y métricas. Consume endpoints de monitores (C-11).

### Modified Capabilities
<!-- Sin cambios en specs existentes — solo consumo de APIs ya definidas. -->

## Impact

- **Frontend**: nuevo feature module `features/comision/` (~8 páginas, componentes asociados, hooks, servicios), nuevo feature module `features/monitores/`
- **Backend**: sin cambios — todos los endpoints necesarios ya existen (C-10, C-11, C-12)
- **Routing**: nuevas rutas anidadas bajo el layout autenticado en App.tsx
- **Permisos**: uso de `RequirePermission` con permisos existentes (`calificaciones:importar`, `analisis:ver`, `comunicacion:enviar`, etc.)
- **Tests**: nuevos tests de componentes con mocks de API vía MSW o similar
