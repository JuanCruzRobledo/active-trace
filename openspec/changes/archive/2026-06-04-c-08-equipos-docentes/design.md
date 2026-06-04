# Design: c-08-equipos-docentes

## Arquitectura

### Componentes Principales

| Componente | Responsabilidad |
|------------|-----------------|
| **EquipoService** | Operaciones de dominio sobre asignaciones como unidad (equipo docente): mis-equipos, asignación masiva, clonación, vigencia, exportación |
| **AsignacionRepository** | Ya existe de C-07. Se extiende con: `bulk_create()`, `list_by_equipo()` (materia × carrera × cohorte), `update_vigencia_en_bloque()` |
| **EquipoRouter** | Endpoints `/api/equipos/*` con permisos `equipos:ver` (mis-equipos) y `equipos:asignar` (gestión) |
| **AuditService** | Ya existe de C-05. Registra `ASIGNACION_MODIFICAR` en cada operación |
| **ExportService** | Genera archivo descargable (CSV) con el detalle del equipo |

### Patrones de Diseño

- **Service Layer**: `EquipoService` encapsula toda la lógica de dominio de equipos, llamando al repository existente
- **Unit of Work** (transaccional): asignación masiva y clonación corren dentro de una sola transacción — si falla un paso, rollback total
- **Repository**: `AsignacionRepository` se extiende con nuevos métodos query, no se modifica la interfaz existente
- **Builder pattern**: construcción de asignaciones masivas a partir de producto cartesiano docentes × (materia × carrera × cohorte × rol)

### Flujo de Datos

#### Asignación Masiva
```
POST /api/equipos/asignacion-masiva
  → EquipoService.asignacion_masiva(data)
    → Validar que todos los usuarios existen en el tenant
    → Generar producto cartesiano: usuarios × [materia, carrera, cohorte, rol, desde, hasta]
    → AsignacionRepository.bulk_create(asignaciones) [transacción]
    → AuditService.log("ASIGNACION_MODIFICAR", ...)
    → Retornar asignaciones creadas
```

#### Clonar Equipo
```
POST /api/equipos/clonar
  → EquipoService.clonar_equipo(origen, destino)
    → Validar que origen existe (materia × carrera × cohorte)
    → Obtener asignaciones vigentes del origen
    → Duplicar cada asignación con: tenant_id, usuario_id, rol, materia_id, carrera_id,
      cohorte_id=destino.cohorte_id, comisiones, responsable_id, desde=destino.desde, hasta=destino.hasta
    → AsignacionRepository.bulk_create(nuevas_asignaciones) [transacción]
    → AuditService.log("ASIGNACION_MODIFICAR", ...)
    → Retornar asignaciones clonadas
```

#### Mis Equipos (docente)
```
GET /api/equipos/mis-equipos?estado=&materia=&rol=&carrera=&cohorte=
  → EquipoService.mis_equipos(usuario_id, filtros)
    → AsignacionRepository.list_by_usuario(usuario_id) + filtros
    → Calcular estado_vigencia para cada una
    → Retornar listado con contexto (materia, carrera, cohorte, rol)
```

#### Modificar Vigencia General
```
PATCH /api/equipos/{equipo_id}/vigencia
  → EquipoService.modificar_vigencia(materia_id, carrera_id, cohorte_id, desde, hasta)
    → AsignacionRepository.update_vigencia_en_bloque(...) [transacción]
    → AuditService.log("ASIGNACION_MODIFICAR", ...)
    → Retornar cantidad de asignaciones afectadas
```

#### Exportar Equipo
```
GET /api/equipos/{equipo_id}/export
  → EquipoService.exportar_equipo(materia_id, carrera_id, cohorte_id)
    → Obtener todas las asignaciones del equipo
    → Generar CSV con columnas: docente, rol, materia, carrera, cohorte, comisiones, desde, hasta, estado_vigencia
    → Retornar archivo descargable
```

## Modelo de Datos

No se requieren nuevas tablas. Se utiliza el modelo `Asignacion` existente (C-07):

```
Asignacion (ya existe)
├── id              : UUID       — PK
├── tenant_id       : UUID       — FK → Tenant
├── usuario_id      : UUID       — FK → Usuario (docente asignado)
├── rol             : enum       — PROFESOR | TUTOR | COORDINADOR | NEXO | ADMIN | FINANZAS
├── materia_id      : UUID       — FK → Materia (nullable)
├── carrera_id      : UUID       — FK → Carrera (nullable)
├── cohorte_id      : UUID       — FK → Cohorte (nullable)
├── comisiones      : lista<texto> — comisiones incluidas
├── responsable_id  : UUID       — FK → Usuario (supervisor)
├── desde           : fecha      — inicio de vigencia
├── hasta           : fecha      — fin de vigencia (nulo = abierta)
├── deleted_at      : fecha      — soft delete
└── estado_vigencia : derivado   — Vigente | Vencida | Sin iniciar (no almacenado)
```

### Permiso nuevo (seed data)

| modulo | accion | descripcion |
|--------|--------|-------------|
| equipos | ver | Ver mis equipos y consultar asignaciones propias |
| equipos | asignar | *(ya existe de C-07)* Gestionar asignaciones de equipo |

### Eventos de auditoría

| Tipo | Acción |
|------|--------|
| `ASIGNACION_MODIFICAR` | asignación masiva, clonación, modificación vigencia |

## APIs

Todos los endpoints bajo el router `/api/equipos`:

### GET /api/equipos/mis-equipos
- **Permiso**: `equipos:ver` (implícitamente scoped al usuario autenticado — no permite ver equipos ajenos)
- **Query params**: `estado`, `materia_id`, `rol`, `carrera_id`, `cohorte_id`
- **Output**: `list[EquipoResponse]` con datos de la asignación + materia_nombre, carrera_nombre, cohorte_nombre
- **Errors**: 200 OK

### GET /api/equipos (gestión de asignaciones — F4.3)
- **Permiso**: `equipos:asignar`
- **Query params**: `materia_id`, `carrera_id`, `cohorte_id`, `usuario_id`, `rol`, `vigente` (bool)
- **Output**: `list[EquipoResponse]`
- **Errors**: 200 OK

### POST /api/equipos/asignacion-masiva
- **Permiso**: `equipos:asignar`
- **Input**:
  ```json
  {
    "usuario_ids": ["uuid1", "uuid2", ...],
    "materia_id": "uuid",
    "carrera_id": "uuid",
    "cohorte_id": "uuid",
    "rol": "PROFESOR",
    "comisiones": ["A", "B"],
    "responsable_id": "uuid",
    "desde": "2026-01-01T00:00:00Z",
    "hasta": "2026-07-31T00:00:00Z"
  }
  ```
- **Output**: `list[AsignacionResponse]` con las asignaciones creadas
- **Errors**: 409 (usuario no existe), 422 (validación)

### POST /api/equipos/clonar
- **Permiso**: `equipos:asignar`
- **Input**:
  ```json
  {
    "origen_materia_id": "uuid",
    "origen_carrera_id": "uuid",
    "origen_cohorte_id": "uuid",
    "destino_materia_id": "uuid",
    "destino_carrera_id": "uuid",
    "destino_cohorte_id": "uuid",
    "destino_desde": "2026-08-01T00:00:00Z",
    "destino_hasta": "2027-02-28T00:00:00Z"
  }
  ```
- **Output**: `ClonarResponse { creadas: int, origen: str, destino: str, asignaciones: list[AsignacionResponse] }`
- **Errors**: 404 (origen no encontrado), 409 (conflicto)

### PATCH /api/equipos/vigencia
- **Permiso**: `equipos:asignar`
- **Input**:
  ```json
  {
    "materia_id": "uuid",
    "carrera_id": "uuid",
    "cohorte_id": "uuid",
    "desde": "2026-03-01T00:00:00Z",
    "hasta": "2026-09-30T00:00:00Z"
  }
  ```
- **Output**: `VigenciaResponse { afectadas: int, desde: date, hasta: date }`
- **Errors**: 404 (no hay asignaciones para ese equipo)

### GET /api/equipos/{equipo_id}/export
- Siendo `equipo_id` la tupla `materia_id-carrera_id-cohorte_id` (pasada como query params compuestos)
- **Permiso**: `equipos:asignar`
- **Query params**: `materia_id`, `carrera_id`, `cohorte_id`
- **Output**: archivo CSV con headers: `docente, documento, rol, materia, carrera, cohorte, comisiones, desde, hasta, estado_vigencia`
- **Errors**: 200 OK (puede devolver CSV vacío si no hay asignaciones)

## Seguridad

- **Identidad desde la sesión**: en `mis-equipos` el `usuario_id` se resuelve desde el JWT — nunca desde un parámetro
- **Multi-tenancy**: todos los queries pasan por `_scope_query()` del repositorio — cada tenant solo ve sus propios datos
- **RBAC**: `equipos:ver` para auto-consulta; `equipos:asignar` para gestión (COORDINADOR, ADMIN)
- **Auditoría**: toda operación de escritura (asignación masiva, clonación, modificación vigencia) registra `ASIGNACION_MODIFICAR`
- **Fail-closed**: sin permiso explícito → 403

## Consideraciones

- **Trade-off**: la clonación no verifica duplicados — si ya existen asignaciones en el destino, el clon agrega nuevas. El coordinador debe verificar antes. Alternativa considerada: clonación con reemplazo (descartado por riesgo de pérdida de datos).
- **Alternativa considerada**: crear un modelo `Equipo` separado con sus propias tablas. Se descartó porque `Asignacion` ya modela la relación perfectamente y agregar otra entidad complejiza el schema sin beneficio real.
- **Asignación masiva**: el producto cartesiano se genera en Python (no en SQL). Para conjuntos grandes (>100 docentes × 1 materia) puede requerir optimización futura con bulk insert directo.
- **Exportación**: se usa CSV como formato estándar (universal, fácil de abrir). No se implementa PDF porque no hay requerimiento de diseño visual.
