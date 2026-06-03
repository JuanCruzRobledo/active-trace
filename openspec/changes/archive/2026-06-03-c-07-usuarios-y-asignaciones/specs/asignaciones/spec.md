## ADDED Requirements

### Requirement: Crear Asignación
El sistema SHALL permitir a usuarios con permiso `equipos:asignar` crear asignaciones que vinculan un usuario con un rol y contexto académico (materia, carrera, cohorte, comisiones). `materia_id`, `carrera_id` y `cohorte_id` son opcionales (asignaciones globales de tenant). La vigencia se define con `desde` y `hasta` (nulo = abierta).

#### Scenario: Creación exitosa de asignación
- **WHEN** un COORDINADOR asigna un PROFESOR a una materia con fechas de vigencia y comisiones específicas
- **THEN** el sistema crea la asignación con estado_vigencia "Vigente" y retorna 201 Created.

#### Scenario: Asignación sin contexto académico (rol global)
- **WHEN** un ADMIN asigna un rol FINANZAS sin materia, carrera ni cohorte
- **THEN** la asignación se crea correctamente como asignación global del tenant.

### Requirement: Listar Asignaciones
El sistema SHALL permitir a usuarios con permiso `equipos:asignar` listar asignaciones del tenant con filtros por materia, carrera, cohorte, usuario, rol y estado de vigencia. Las asignaciones vencidas SHALL incluirse en el listado con estado "Vencida".

#### Scenario: Listado filtrado por materia
- **WHEN** un COORDINADOR lista asignaciones filtradas por una materia específica
- **THEN** el sistema retorna SOLO las asignaciones vinculadas a esa materia en el tenant.

#### Scenario: Historial incluye asignaciones vencidas
- **WHEN** un ADMIN lista todas las asignaciones de un usuario
- **THEN** el listado incluye tanto asignaciones vigentes como vencidas, cada una con su estado_vigencia correspondiente.

### Requirement: Modificar Asignación
El sistema SHALL permitir a usuarios con permiso `equipos:asignar` modificar los campos de una asignación existente (rol, contexto, responsable_id, vigencia).

#### Scenario: Extensión de vigencia
- **WHEN** un COORDINADOR extiende la fecha `hasta` de una asignación próxima a vencer
- **THEN** la asignación se actualiza y su estado_vigencia se recalcula como "Vigente".

### Requirement: Baja lógica de Asignación
El sistema SHALL permitir a usuarios con permiso `equipos:asignar` realizar baja lógica de asignaciones. La asignación NO se elimina físicamente; se conserva para histórico.

#### Scenario: Soft-delete de asignación
- **WHEN** un COORDINADOR elimina una asignación
- **THEN** la asignación se marca como eliminada (soft-delete) pero permanece accesible en consultas históricas.

### Requirement: Vigencia y autorización
Una asignación vencida NO otorga permisos al usuario. El sistema SHALL evaluar la vigencia en tiempo real basándose en las fechas `desde`/`hasta`. El `estado_vigencia` es un campo derivado (no almacenado).

#### Scenario: Asignación vencida no autoriza
- **WHEN** un usuario con una asignación vencida intenta acceder a un endpoint protegido por los permisos de esa asignación
- **THEN** el sistema deniega el acceso (403 Forbidden).

#### Scenario: Asignación vigente autoriza
- **WHEN** un usuario con una asignación vigente intenta acceder a un endpoint protegido por los permisos de esa asignación
- **THEN** el sistema permite el acceso.

### Requirement: Jerarquía responsable
Las asignaciones SHALL soportar un campo `responsable_id` que vincula a quién rinde cuentas el asignado (jerarquía docente: coordinador responsable).

#### Scenario: Asignación con responsable
- **WHEN** un COORDINADOR asigna un TUTOR a una materia con un PROFESOR como responsable
- **THEN** la asignación guarda la referencia al responsable y puede consultarse la jerarquía.

### Requirement: Multi-rol
Un usuario SHALL poder tener múltiples asignaciones activas simultáneamente, con distintos roles y contextos.

#### Scenario: Usuario con dos roles simultáneos
- **WHEN** un usuario tiene una asignación como PROFESOR en una materia y otra como COORDINADOR en otra materia distinta
- **THEN** ambas asignaciones coexisten y el usuario ejerce los permisos de cada rol según el contexto de la operación.
