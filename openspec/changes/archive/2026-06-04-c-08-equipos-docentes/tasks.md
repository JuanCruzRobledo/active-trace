# Tasks: c-08-equipos-docentes

## Implementation Checklist

### Grupo 1: Permisos y Esquemas
- [x] 1.1 Crear schema `EquipoResponse` en `backend/app/schemas/equipo.py` con: id, usuario_id, rol, materia_id, carrera_id, cohorte_id, comisiones, responsable_id, desde, hasta, estado_vigencia, materia_nombre, carrera_nombre, cohorte_nombre, created_at, updated_at
- [x] 1.2 Crear schema `AsignacionMasivaRequest` con: `usuario_ids: list[UUID]`, `materia_id`, `carrera_id`, `cohorte_id`, `rol`, `comisiones`, `responsable_id`, `desde`, `hasta`
- [x] 1.3 Crear schema `ClonarEquipoRequest` con: origen y destino (materia_id, carrera_id, cohorte_id, desde, hasta)
- [x] 1.4 Crear schema `VigenciaRequest` con: `materia_id`, `carrera_id`, `cohorte_id`, `desde`, `hasta`
- [x] 1.5 Crear schema `VigenciaResponse` con: `afectadas: int`, `desde`, `hasta`
- [x] 1.6 Crear schema `ClonarResponse` con: `creadas: int`, `origen: str`, `destino: str`, `asignaciones: list[AsignacionResponse]`
- [x] 1.7 Agregar seed del permiso `equipos:ver` en migración (o seed data existente)

### Grupo 2: Extensión de Repository
- [x] 2.1 Agregar método `bulk_create(asignaciones: list[Asignacion]) -> list[Asignacion]` en `AsignacionRepository` (insert masivo con transacción)
- [x] 2.2 Agregar método `list_by_equipo(materia_id, carrera_id, cohorte_id) -> list[Asignacion]` que obtiene todas las asignaciones de un equipo
- [x] 2.3 Agregar método `update_vigencia_en_bloque(materia_id, carrera_id, cohorte_id, desde, hasta) -> int` que actualiza todas las asignaciones del equipo en una query

### Grupo 3: EquipoService (nuevo)
- [x] 3.1 Crear `EquipoService` en `backend/app/services/equipo_service.py` con constructor que recibe `session`, `tenant_id`, `current_user_id`
- [x] 3.2 Implementar `mis_equipos(usuario_id, filtros)`: retorna asignaciones del usuario con contexto (materia_nombre, carrera_nombre, cohorte_nombre)
- [x] 3.3 Implementar `asignacion_masiva(data: AsignacionMasivaRequest)`: validar usuarios, generar producto cartesiano, bulk_create, audit
- [x] 3.4 Implementar `clonar_equipo(data: ClonarEquipoRequest)`: validar origen, obtener vigentes, duplicar con nuevo cohorte/fechas, bulk_create, audit
- [x] 3.5 Implementar `modificar_vigencia(data: VigenciaRequest)`: update_vigencia_en_bloque, audit
- [x] 3.6 Implementar `exportar_equipo(materia_id, carrera_id, cohorte_id)`: listar asignaciones del equipo y retornar datos estructurados

### Grupo 4: Router /api/equipos
- [x] 4.1 Crear router `backend/app/api/v1/routers/equipos.py` con prefijo `/api`
- [x] 4.2 Implementar `GET /api/equipos/mis-equipos` con permiso `equipos:ver` (scoped al usuario autenticado)
- [x] 4.3 Implementar `GET /api/equipos` (gestión, F4.3) con permiso `equipos:asignar` y filtros
- [x] 4.4 Implementar `POST /api/equipos/asignacion-masiva` con permiso `equipos:asignar`
- [x] 4.5 Implementar `POST /api/equipos/clonar` con permiso `equipos:asignar`
- [x] 4.6 Implementar `PATCH /api/equipos/vigencia` con permiso `equipos:asignar`
- [x] 4.7 Implementar `GET /api/equipos/export` con permiso `equipos:asignar` y response como CSV descargable
- [x] 4.8 Registrar router en la app (backend/app/api/v1/router.py o main.py)

### Grupo 5: Tests
- [x] 5.1 Test: Mis equipos retorna solo asignaciones del usuario autenticado
- [x] 5.2 Test: Mis equipos con filtros (estado, materia, rol)
- [x] 5.3 Test: Asignación masiva exitosa — crear N asignaciones en una transacción
- [x] 5.4 Test: Asignación masiva con usuario inexistente → 409 BusinessError
- [x] 5.5 Test: Clonar equipo exitoso — verificar que las asignaciones clonadas usan las fechas del destino
- [x] 5.6 Test: Clonar equipo con origen inexistente → 404
- [x] 5.7 Test: Modificar vigencia general — verificar que todas las asignaciones del equipo se actualizan
- [x] 5.8 Test: Modificar vigencia sin asignaciones → 404
- [x] 5.9 Test: Exportar equipo — verificar formato CSV con headers correctos
- [x] 5.10 Test: Exportar equipo sin datos — CSV vacío con headers
- [x] 5.11 Test: Seguridad — mis-equipos no permite ver asignaciones de otro usuario (basado en sesión)
- [x] 5.12 Test: Seguridad — endpoint sin permiso retorna 403
- [x] 5.13 Test: Auditoría — cada operación de escritura genera ASIGNACION_MODIFICAR

## Dependencias
- `C-07` usuarios-y-asignaciones (modelo Asignacion, repo, schemas base)
- `C-05` audit-log (AuditService para registrar operaciones)
- `C-04` rbac-permisos-finos (dependencia require_permission)
- `openspec/specs/asignaciones/spec.md` — spec de asignaciones base
- `openspec/specs/rbac-finos/spec.md` — spec de permisos finos

## Notas de Implementación
- **Strict TDD obligatorio**: cada task empieza con test → código mínimo → triangulación → refactor
- **No se necesita migración de tablas**: solo seed del permiso `equipos:ver`
- **Transacciones**: `bulk_create` debe usar `session.add_all()` dentro de un `async with session.begin()` explícito o delegar en el commit del caller
- **Clonación**: solo se clonan asignaciones vigentes (las que están dentro de su rango de fechas al momento de la operación). Asignaciones soft-deleted no se clonan.
- **Export CSV**: usar `csv.writer` de la stdlib de Python. Headers en español: `docente, documento, rol, materia, carrera, cohorte, comisiones, desde, hasta, estado_vigencia`
- **Auditoría**: grabar `ASIGNACION_MODIFICAR` con metadata: `{operacion: "asignacion_masiva"|"clonar"|"modificar_vigencia", cantidad: int, materia_id, carrera_id, cohorte_id}`
- **Equipo identification**: un "equipo" se identifica por la tupla (materia_id, carrera_id, cohorte_id)
