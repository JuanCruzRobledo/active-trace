## ADDED Requirements

### Requirement: Aviso tiene alcance y severidad
Todo aviso SHALL tener un alcance (Global, PorMateria, PorCohorte, PorRol) y una severidad (Info, Advertencia, Crítico). El alcance determina qué usuarios ven el aviso; la severidad determina su prioridad en la timeline.

#### Scenario: Crear aviso con alcance Global y severidad Crítico
- **WHEN** un COORDINADOR crea un aviso con alcance Global y severidad Crítico
- **THEN** el aviso se guarda con esos valores y aparece en la timeline de todos los usuarios del tenant

#### Scenario: Crear aviso con alcance PorMateria
- **WHEN** un COORDINADOR crea un aviso con alcance PorMateria y materia_id específico
- **THEN** el aviso solo aparece en la timeline de usuarios que tienen asignaciones en esa materia

---

### Requirement: Aviso tiene vigencia programada
Todo aviso SHALL tener una fecha/hora de inicio y una fecha/hora de fin de vigencia. El aviso solo es visible dentro de ese rango temporal.

#### Scenario: Aviso antes de vigencia no visible
- **WHEN** un usuario consulta su timeline antes del `inicio_en` de un aviso
- **THEN** el aviso no aparece en la timeline

#### Scenario: Aviso después de vigencia no visible
- **WHEN** un usuario consulta su timeline después del `fin_en` de un aviso
- **THEN** el aviso no aparece en la timeline

#### Scenario: Aviso dentro de vigencia es visible
- **WHEN** un usuario consulta su timeline dentro del rango `inicio_en`–`fin_en` de un aviso
- **THEN** el aviso aparece en la timeline

---

### Requirement: Timeline ordenada por severidad y orden
La timeline de avisos activos SHALL ordenarse primero por severidad descendente (Crítico → Advertencia → Info), luego por orden ascendente (campo numérico), luego por created_at descendente.

#### Scenario: Avisos ordenados por severidad
- **WHEN** un usuario consulta su timeline y hay avisos de distintas severidades
- **THEN** los avisos Crítico aparecen primero, luego Advertencia, luego Info

#### Scenario: Avisos de misma severidad ordenados por campo orden
- **WHEN** un usuario consulta su timeline y hay dos avisos de la misma severidad
- **THEN** el aviso con menor valor en `orden` aparece primero

---

### Requirement: Acknowledge obligatorio configurable por aviso
Si un aviso tiene `requiere_ack = true`, el usuario SHALL poder confirmar explícitamente que lo leyó. El sistema SHALL registrar la confirmación con timestamp.

#### Scenario: Acknowledge exitoso
- **WHEN** un usuario hace POST /api/avisos/{id}/acknowledge en un aviso que requiere ack
- **THEN** se crea un registro en AcknowledgmentAviso con el usuario y timestamp actual

#### Scenario: Acknowledge duplicado rechazado
- **WHEN** un usuario intenta acknowledge el mismo aviso dos veces
- **THEN** el sistema rechaza con 409 Conflict

---

### Requirement: Tracking de acknowledgments con agregados
El sistema SHALL exponer para cada aviso: cantidad total de usuarios en el alcance, cantidad de acknowledgments registrados, porcentaje de cumplimiento y lista de usuarios que ya acknowledge.

#### Scenario: Tracking de aviso global
- **WHEN** un COORDINADOR consulta el tracking de un aviso Global
- **THEN** el sistema retorna total_usuarios = todos los usuarios activos del tenant, total_ack = los que acknowledge, porcentaje = total_ack / total_usuarios * 100

#### Scenario: Tracking de aviso por materia
- **WHEN** un COORDINADOR consulta el tracking de un aviso PorMateria
- **THEN** el sistema retorna total_usuarios = usuarios con asignaciones en esa materia, total_ack = los que acknowledge

---

### Requirement: Eliminación segura según estado
Si un aviso nunca tuvo acknowledgments, SHALL poder eliminarse físicamente (hard delete). Si ya tuvo acknowledgments, SHALL aplicarse soft delete (deleted_at) para conservar el histórico.

#### Scenario: Hard delete sin acknowledgments
- **WHEN** un COORDINADOR elimina un aviso que nunca fue acknowledge por nadie
- **THEN** el registro se elimina físicamente de la base de datos

#### Scenario: Soft delete con acknowledgments
- **WHEN** un COORDINADOR elimina un aviso que ya tiene acknowledgments
- **THEN** el registro se marca con deleted_at y permanece en la base de datos

---

### Requirement: Permisos de gestión y lectura
Solo usuarios con permiso `avisos:gestionar` SHALL poder crear, editar y eliminar avisos. Todos los usuarios autenticados SHALL poder ver la timeline y hacer acknowledge (requisito: estar autenticado).

#### Scenario: Gestión sin permiso retorna 403
- **WHEN** un usuario sin permiso `avisos:gestionar` intenta crear un aviso
- **THEN** el sistema retorna 403 Forbidden

#### Scenario: Timeline accesible a cualquier autenticado
- **WHEN** cualquier usuario autenticado consulta GET /api/avisos/timeline
- **THEN** el sistema retorna 200 con la lista de avisos activos para su perfil

---

### Requirement: Auditoría de acciones sobre avisos
Cada creación de aviso SHALL generar un evento de auditoría `AVISO_CREAR`. Cada acknowledgment SHALL generar un evento `AVISO_ACK`.

#### Scenario: Auditoría al crear aviso
- **WHEN** un COORDINADOR crea un aviso
- **THEN** se registra un AuditLog con accion = "AVISO_CREAR", actor_id, detalle con id y título del aviso

#### Scenario: Auditoría al acknowledge
- **WHEN** un usuario hace acknowledge de un aviso
- **THEN** se registra un AuditLog con accion = "AVISO_ACK", actor_id, detalle con aviso_id
