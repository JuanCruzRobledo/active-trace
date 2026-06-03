## ADDED Requirements

### Requirement: Crear Usuario
El sistema SHALL permitir a usuarios con rol ADMIN crear nuevos usuarios en su tenant. Los campos email, dni, cuil, cbu y alias_cbu SHALL almacenarse cifrados con AES-256 en reposo. El par (tenant_id, email) MUST ser único para usuarios no eliminados. El legajo es un atributo de negocio opcional, no una credencial.

#### Scenario: Creación exitosa de usuario
- **WHEN** un ADMIN envía datos válidos para crear un usuario (nombre, apellidos, email, dni, cuil)
- **THEN** el sistema devuelve 201 Created, el usuario se persiste con tenant_id, los campos PII se almacenan cifrados, y el email es retornado enmascarado en la respuesta.

#### Scenario: Fallo por email duplicado
- **WHEN** un ADMIN intenta crear un usuario con un email que ya existe en el mismo tenant (para un usuario no eliminado)
- **THEN** el sistema rechaza la operación con error 409 Conflict.

#### Scenario: Email duplicado en distinto tenant es válido
- **WHEN** un ADMIN del Tenant A crea un usuario con email "docente@mail.com" y un ADMIN del Tenant B crea otro usuario con el mismo email
- **THEN** ambas operaciones son exitosas (el alcance de unicidad es por tenant).

### Requirement: Listar Usuarios
El sistema SHALL permitir a usuarios ADMIN listar los usuarios del tenant con filtros opcionales (nombre, email, estado, rol mediante join con asignaciones) y paginación.

#### Scenario: Listado paginado de usuarios
- **WHEN** un ADMIN solicita GET /api/admin/usuarios
- **THEN** el sistema retorna una lista paginada de usuarios del tenant, con campos PII enmascarados.

#### Scenario: Filtro por estado
- **WHEN** un ADMIN filtra usuarios por estado "Inactivo"
- **THEN** SOLO se retornan usuarios con estado Inactivo en ese tenant.

### Requirement: Editar Usuario
El sistema SHALL permitir a usuarios ADMIN modificar datos de un usuario existente en su tenant.

#### Scenario: Edición de datos no sensibles
- **WHEN** un ADMIN actualiza el nombre y apellidos de un usuario
- **THEN** el sistema actualiza solo esos campos y retorna 200 OK.

#### Scenario: Edición de email existente
- **WHEN** un ADMIN cambia el email de un usuario a uno ya ocupado en el mismo tenant
- **THEN** el sistema rechaza con 409 Conflict.

### Requirement: Baja lógica de Usuario (soft-delete)
El sistema SHALL permitir a usuarios ADMIN realizar baja lógica de usuarios. El usuario NO se elimina físicamente; se marca como Inactivo. El partial unique index (tenant_id, email) MUST excluir usuarios inactivos para permitir re-uso del email.

#### Scenario: Soft-delete exitoso
- **WHEN** un ADMIN marca un usuario como Inactivo
- **THEN** el sistema persiste el cambio (UPDATE, no DELETE), y el email del usuario puede ser re-usado por otro usuario del mismo tenant.

#### Scenario: Consulta de usuario eliminado
- **WHEN** un ADMIN consulta un usuario que fue marcado como Inactivo
- **THEN** el usuario aparece en la respuesta con estado "Inactivo".

### Requirement: PII cifrada no expuesta
El sistema SHALL garantizar que los campos PII (email, dni, cuil, cbu, alias_cbu) nunca se expongan en texto plano en logs de aplicación, respuestas HTTP ni mensajes de error. Los schemas de respuesta SHALL retornar estos campos enmascarados o excluidos.

#### Scenario: Email no visible en log
- **WHEN** se realiza cualquier operación sobre usuarios
- **THEN** los logs del sistema NO contienen los valores en texto plano de email, dni, cuil, cbu ni alias_cbu.

#### Scenario: Respuesta HTTP sin PII en texto plano
- **WHEN** un ADMIN lista o consulta usuarios vía API
- **THEN** la respuesta JSON contiene los campos PII enmascarados (ej: "n***@***.com") o excluidos del response.
