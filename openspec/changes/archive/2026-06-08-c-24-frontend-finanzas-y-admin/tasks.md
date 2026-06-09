# Tasks: c-24-frontend-finanzas-y-admin

## Implementation Checklist

> TDD activo: para cada página/componente con lógica, escribir primero el test (RED), luego la implementación mínima (GREEN), triangular y refactorizar. Schemas Zod con `.strict()` (regla dura). Archivos < 200 LOC; dividir si crecen. Reutilizar shared components existentes (`FilterableTable`, `ContextoAcademicoSelector`, `ConfirmDialog`, `FormField`, etc.). NO modificar backend. Prefijos de API reales: `/api/...` (no `/api/v1/...`).

### Fase 0: Navegación y rutas
- [x] 0.1 Actualizar `AppLayout` con secciones "Finanzas" y "Administración" (visibles según permisos del usuario)
- [x] 0.2 Agregar rutas protegidas en `App.tsx` para todos los módulos nuevos con sus `<RequirePermission>` correspondientes

### Fase 1: Módulo Liquidaciones — servicios y tipos
- [x] 1.1 Crear `features/liquidaciones/types/liquidaciones.ts` con schemas Zod (`.strict()`): liquidación, detalle docente, segmento, KPIs, salario base, plus, clave plus, factura
- [x] 1.2 Crear `features/liquidaciones/services/liquidaciones.ts` con endpoints: calcular, listar, detalle, cerrar, grilla (salarios-base, salarios-plus, claves-plus), facturas (listar/crear/abonar)
- [x] 1.3 Crear `features/liquidaciones/hooks/useLiquidaciones.ts` (queries + mutaciones con invalidación)

### Fase 2: Liquidaciones — vista segmentada del período (F10.1, F10.6)
- [x] 2.1 Crear `LiquidacionKpiHeader.tsx` — cabecera con "Total sin factura" y "Total con factura"
- [x] 2.2 Crear `SegmentoLiquidacionTable.tsx` — tabla reutilizable para un segmento
- [x] 2.3 Crear `LiquidacionPeriodoPage.tsx` — tres segmentos (general / NEXO / facturan) + KPIs + filtros (cohorte, mes, docente)
- [x] 2.4 Crear `DetalleDocenteDialog.tsx` — vista previa del detalle individual (rol, comisiones, base, plus, total)

### Fase 3: Liquidaciones — cierre e historial (F10.2, F10.3)
- [x] 3.1 Implementar acción "Cerrar liquidación" con `ConfirmDialog` + invalidación; deshabilitar acciones si está cerrada
- [x] 3.2 Crear `HistorialLiquidacionesPage.tsx` — listado filtrable de liquidaciones cerradas con acceso a detalle

### Fase 4: Liquidaciones — grilla salarial (F10.4)
- [x] 4.1 Crear `GrillaSalarialPage.tsx` — secciones salarios base y plus con `FilterableTable`
- [x] 4.2 Formulario de alta de salario base (rol, importe, vigencia desde/hasta) con RHF + Zod
- [x] 4.3 Formulario de alta de plus (clave, rol, descripción, importe, vigencia) con RHF + Zod

### Fase 5: Liquidaciones — facturas (F10.5)
- [x] 5.1 Crear `FacturasPage.tsx` — `FilterableTable` con filtros (docente, estado, rango de fechas, búsqueda)
- [x] 5.2 Implementar acción "Marcar abonada" (`POST .../abonar`) con confirmación e invalidación

### Fase 6: Módulo Estructura Académica (F5.1, F5.2, materias)
- [x] 6.1 Crear `features/estructura-academica/types/estructura.ts` (Zod `.strict()`: carrera, cohorte, materia)
- [x] 6.2 Crear `features/estructura-academica/services/estructura.ts` (carreras, cohortes, materias — prefix `/api/admin`)
- [x] 6.3 Crear `features/estructura-academica/hooks/useEstructura.ts`
- [x] 6.4 Crear `CarrerasPage.tsx` — ABM (listar/crear/editar/cambiar estado) con código y nombre
- [x] 6.5 Crear `CohortesPage.tsx` — ABM con nombre, año, vigencia desde/hasta, estado
- [x] 6.6 Crear `MateriasPage.tsx` — ABM de materias

### Fase 7: Módulo Usuarios del Tenant (F4.1)
- [x] 7.1 Crear `features/usuarios-tenant/types/usuarios.ts` (Zod `.strict()`: usuario, datos fiscales/bancarios, rol)
- [x] 7.2 Crear `features/usuarios-tenant/services/usuarios.ts` (CRUD — prefix `/api/admin/usuarios`)
- [x] 7.3 Crear `features/usuarios-tenant/hooks/useUsuariosTenant.ts`
- [x] 7.4 Crear `UsuariosListPage.tsx` — listado filtrable con rol y estado
- [x] 7.5 Crear `UsuarioFormPage.tsx` — alta/edición + activar/desactivar (nombre, fiscal, bancario, regional, rol, modalidad)

### Fase 8: Módulo Auditoría (F9.1, F9.2, FL-11)
- [x] 8.1 Crear `features/auditoria/types/auditoria.ts` (Zod `.strict()`: acciones-por-dia, comunicaciones, interacciones, ultima-accion, log)
- [x] 8.2 Crear `features/auditoria/services/auditoria.ts` (prefix `/api/auditoria`: acciones-por-dia, comunicaciones-por-docente, interacciones-por-docente-materia, ultimas-acciones, log)
- [x] 8.3 Crear `features/auditoria/hooks/useAuditoria.ts`
- [x] 8.4 Crear filtros compartidos (rango de fechas, materia, usuario, estado) y sub-paneles: `AccionesPorDiaChart`, `ComunicacionesPorDocentePanel`, `InteraccionesPanel`, últimas acciones
- [x] 8.5 Crear `AuditoriaPanelPage.tsx` — arma el panel con las sub-vistas + filtros
- [x] 8.6 Crear `LogAuditoriaPage.tsx` — log completo con todos los campos (fecha/hora, usuario, materia, acción, registros, IP, user agent)

### Fase 9: Tests (TDD)
- [x] 9.1 Test: `LiquidacionPeriodoPage` renderiza los tres segmentos y los KPIs; los docentes que facturan no suman al total
- [x] 9.2 Test: cierre de liquidación — confirmación dispara la mutación; liquidación cerrada deshabilita acciones
- [x] 9.3 Test: ABM grilla salarial — alta de salario base y de plus (formulario válido e inválido)
- [x] 9.4 Test: facturas — filtro por estado y acción "marcar abonada"
- [x] 9.5 Test: panel de auditoría con filtros (rango de fechas, materia, usuario) actualiza las sub-vistas

## Dependencias
- `C-21` — Frontend shell + auth (AppLayout, ProtectedRoute, RequirePermission)
- `C-18` — Backend liquidaciones, grilla salarial, facturas (`liquidaciones.py`)
- `C-19` — Backend auditoría y métricas (`auditoria.py`)
- `C-06` — Backend estructura académica (`admin_estructura.py`)
- `C-07` — Backend usuarios del tenant (`usuarios.py`)
- `C-22` / `C-23` — Frontend (patrón de referencia + shared components reutilizables)

## Notas de Implementación
- Seguir exactamente el patrón de C-22/C-23: `types/` → `services/` → `hooks/` → `pages/`
- Reutilizar shared components existentes; NO recrear `FilterableTable`, `ConfirmDialog`, etc.
- Prefijos de API reales: `/api/liquidaciones`, `/api/admin`, `/api/auditoria` (verificados en los routers)
- Validar los DTOs de respuesta contra los schemas Pydantic reales de cada router durante apply
- El cierre de liquidación es irreversible → siempre detrás de `ConfirmDialog`
- Los docentes que facturan se muestran segregados e informativos, NUNCA sumados al total general (RN-35)
- El menú muestra solo las secciones permitidas según los permisos del usuario autenticado
- No modificar backend — solo frontend
