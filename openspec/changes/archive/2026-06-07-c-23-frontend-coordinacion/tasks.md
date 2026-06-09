# Tasks: c-23-frontend-coordinacion

## Implementation Checklist

### Fase 0: Shared Infrastructure
- [x] 0.1 Crear `FilterableTable` component en `frontend/src/shared/components/FilterableTable.tsx` (búsqueda, filtros, paginación, ordenamiento, export CSV, estados vacío/carga/error)
- [x] 0.2 Crear `ContextoAcademicoSelector` component en `frontend/src/shared/components/ContextoAcademicoSelector.tsx` (selectores materia × carrera × cohorte en cascada)
- [x] 0.3 Crear `ConfirmDialog` component en `frontend/src/shared/components/ConfirmDialog.tsx`
- [x] 0.4 Actualizar `AppLayout` con menú de navegación para sección "Coordinación"
- [x] 0.5 Agregar rutas protegidas en `App.tsx` para todos los nuevos módulos con sus permisos correspondientes

### Fase 1: Módulo Equipos Docentes
- [x] 1.1 Crear `services/equipos.ts` con todos los endpoints (mis-equipos, asignaciones, masiva, clonar, vigencia, exportar)
- [x] 1.2 Crear types/schemas Zod en `types/equipos.ts`
- [x] 1.3 Crear hooks TanStack Query en `hooks/useEquipos.ts`
- [x] 1.4 Crear `MisEquiposPage.tsx` — vista del docente con sus equipos, filtros por estado/materia/rol/carrera/cohorte
- [x] 1.5 Crear `AsignacionesPage.tsx` — vista de coordinación de todas las asignaciones activas del tenant
- [x] 1.6 Crear `AsignacionMasivaPage.tsx` — formulario con ContextoAcademicoSelector + selección múltiple de docentes
- [x] 1.7 Crear `ClonarEquipoPage.tsx` — formulario: seleccionar equipo origen → seleccionar destino → confirmar clonación
- [x] 1.8 Crear `VigenciaEquipoPage.tsx` — formulario para actualizar fechas de vigencia de un equipo
- [x] 1.9 Crear `ExportarEquipoPage.tsx` — seleccionar equipo y descargar archivo

### Fase 2: Módulo Avisos
- [x] 2.1 Crear `services/avisos.ts` (CRUD avisos + timeline + acknowledge + tracking)
- [x] 2.2 Crear types/schemas Zod en `types/avisos.ts`
- [x] 2.3 Crear hooks TanStack Query en `hooks/useAvisos.ts`
- [x] 2.4 Crear `AvisosListPage.tsx` — listado filtrable de avisos con indicadores de estado activo/inactivo
- [x] 2.5 Crear `AvisoFormPage.tsx` — formulario completo (create/edit): alcance, severidad, vigencia, roles destino, require_ack, contenido rich text
- [x] 2.6 Crear `AvisoDetailPage.tsx` — detalle + timeline + tracking de acknowledgments
- [x] 2.7 Crear `AckTrackingPanel.tsx` — panel que muestra quién confirmó y quién falta

### Fase 3: Módulo Tareas Internas
- [x] 3.1 Crear `services/tareas.ts` (CRUD tareas + mis tareas + comentarios)
- [x] 3.2 Crear types/schemas Zod en `types/tareas.ts`
- [x] 3.3 Crear hooks TanStack Query en `hooks/useTareas.ts`
- [x] 3.4 Crear `MisTareasPage.tsx` — vista del docente con tareas asignadas, filtros por estado/materia
- [x] 3.5 Crear `AsignarTareaPage.tsx` — formulario: materia, docente asignado, descripción, criterio de cierre
- [x] 3.6 Crear `TareasAdminPage.tsx` — vista global de coordinación con filtros avanzados
- [x] 3.7 Crear `TareaDetailPanel.tsx` — detalle de tarea con timeline de estados + hilo de comentarios

### Fase 4: Módulo Encuentros (Admin)
- [x] 4.1 Crear `services/encuentros.ts` (admin: listar todos los encuentros del tenant)
- [x] 4.2 Crear types/schemas Zod en `types/encuentros.ts`
- [x] 4.3 Crear hooks TanStack Query en `hooks/useEncuentros.ts`
- [x] 4.4 Crear `EncuentrosAdminPage.tsx` — tabla filtrable de todos los encuentros con indicadores de estado (realizado/pendiente/cancelado)

### Fase 5: Módulo Coloquios
- [x] 5.1 Crear `services/coloquios.ts` (métricas, convocatorias CRUD, importar alumnos, admin global)
- [x] 5.2 Crear types/schemas Zod en `types/coloquios.ts`
- [x] 5.3 Crear hooks TanStack Query en `hooks/useColoquios.ts`
- [x] 5.4 Crear `ColoquiosPanelPage.tsx` — panel con métricas (totales, instancias activas, reservas, notas registradas)
- [x] 5.5 Crear `ConvocatoriaFormPage.tsx` — formulario create/edit convocatoria con selector de días y cupos
- [x] 5.6 Crear `ConvocatoriaListPage.tsx` — listado de convocatorias activas con métricas operativas
- [x] 5.7 Crear `ColoquiosAdminPage.tsx` — gestión global: convocatorias, registro académico, agenda de reservas

### Fase 6: Módulo Guardias
- [x] 6.1 Crear `services/guardias.ts` (CRUD guardias + exportar)
- [x] 6.2 Crear types/schemas Zod en `types/guardias.ts`
- [x] 6.3 Crear hooks TanStack Query en `hooks/useGuardias.ts`
- [x] 6.4 Crear `GuardiasPage.tsx` — tabla filtrable con registro de guardias + formulario de alta

### Fase 7: Módulo Programas
- [x] 7.1 Crear `services/programas.ts` (CRUD programas + upload)
- [x] 7.2 Crear types/schemas Zod en `types/programas.ts`
- [x] 7.3 Crear hooks TanStack Query en `hooks/useProgramas.ts`
- [x] 7.4 Crear `ProgramasPage.tsx` — listado + formulario de subida con ContextoAcademicoSelector

### Fase 8: Módulo Fechas Académicas
- [x] 8.1 Crear `services/fechas-academicas.ts` (CRUD + lms-export)
- [x] 8.2 Crear types/schemas Zod en `types/fechas-academicas.ts`
- [x] 8.3 Crear hooks TanStack Query en `hooks/useFechasAcademicas.ts`
- [x] 8.4 Crear `FechasAcademicasPage.tsx` — listado tabular + calendario visual + formulario create/edit + botón de export LMS

### Fase 9: Setup de Cuatrimestre (FL-03)
- [x] 9.1 Crear `services/setup-cuatrimestre.ts`
- [x] 9.2 Crear types/schemas Zod en `types/setup-cuatrimestre.ts`
- [x] 9.3 Crear hooks TanStack Query en `hooks/useSetupCuatrimestre.ts`
- [x] 9.4 Crear `SetupCuatrimestreWizard.tsx` — flujo multi-paso:
      Paso 1: Crear cohorte
      Paso 2: Clonar equipo (o saltar)
      Paso 3: Ajustar asignaciones
      Paso 4: Cargar programas
      Paso 5: Cargar fechas de evaluaciones
      Paso 6: Publicar aviso de bienvenida
      Paso 7: Resumen + confirmación

### Fase 10: Monitores — Vista General (F2.7) y Vista Coordinación (F2.9)
- [x] 10.1 Crear `services/monitores.ts` (general + seguimiento con rango de fechas) — extender el existente si aplica
- [x] 10.2 Crear types/schemas Zod en `types/monitores.ts`
- [x] 10.3 Crear hooks en `hooks/useMonitorGeneral.ts` y actualizar `useMonitorSeguimiento.ts`
- [x] 10.4 Crear/mejorar `MonitoresPage.tsx` para soportar ambas vistas (general + seguimiento) con tabs
- [x] 10.5 Agregar filtro de rango de fechas en vista de coordinación (F2.9)

### Fase 11: Tests
- [x] 11.1 Test: FilterableTable renderiza con datos, filtros, paginación
- [x] 11.2 Test: ABM avisos (crear, editar, eliminar vía mock)
- [x] 11.3 Test: Asignación masiva de docentes — formulario válido e inválido
- [x] 11.4 Test: Workflow de tarea (crear, cambiar estado, agregar comentario)
- [x] 11.5 Test: Filtros de monitor general y seguimiento

## Dependencias
- `C-21` — Frontend shell + auth (AppLayout, ProtectedRoute, RequirePermission)
- `C-08` — Backend equipos docentes (routers, services, repositories)
- `C-13` — Backend encuentros (routers, services)
- `C-14` — Backend coloquios (routers, services)
- `C-15` — Backend avisos + acknowledgment (routers, services)
- `C-16` — Backend tareas internas (routers, services)
- `C-17` — Backend programas y fechas académicas (routers, services)
- `C-22` — Frontend comisiones y monitores (patrón de referencia para feature modules)

## Notas de Implementación
- Seguir exactamente el mismo patrón de C-22: `services/` → `hooks/` → `pages/` con TanStack Query
- Todos los schemas Zod con `extra: "forbid"` (regla dura del proyecto)
- Componentes <200 LOC por archivo; si crece, dividir en sub-componentes
- Usar `FilterableTable` compartido (task 0.1) para todas las tablas con filtros
- No modificar backend — solo frontend
- El menú de navegación debe mostrar solo las secciones que el usuario tiene permiso de ver (basado en los permisos del usuario autenticado)
