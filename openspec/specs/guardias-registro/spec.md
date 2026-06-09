## ADDED Requirements

### Requirement: Registrar guardia (F6.6)

El sistema SHALL permitir a TUTOR y PROFESOR (con permiso `guardias:registrar`) registrar una guardia de atención, especificando: materia, carrera, cohorte, día de la semana, horario (rango) y comentarios opcionales. COORDINADOR/ADMIN puede registrar guardias en nombre de cualquier docente.

#### Scenario: TUTOR registra su propia guardia
- **WHEN** un TUTOR registra una guardia con materia, día y horario
- **THEN** el sistema crea la guardia con estado "Pendiente" y retorna 201 Created

#### Scenario: COORDINADOR registra guardia para un docente
- **WHEN** un COORDINADOR registra una guardia especificando un TUTOR mediante asignacion_id
- **THEN** la guardia se crea asociada a ese TUTOR

### Requirement: Listar guardias con filtros

El sistema SHALL permitir listar guardias con filtros por materia, usuario (docente), rango de fechas y estado. El TUTOR ve sus propias guardias. COORDINADOR/ADMIN ve todas.

#### Scenario: TUTOR lista sus propias guardias
- **WHEN** un TUTOR lista sus guardias
- **THEN** el sistema retorna solo las guardias donde el TUTOR es el asignado

#### Scenario: COORDINADOR lista guardias del tenant
- **WHEN** un COORDINADOR lista guardias con filtro por materia
- **THEN** el sistema retorna todas las guardias de esa materia, de cualquier docente

### Requirement: Editar estado y comentarios de guardia

El sistema SHALL permitir a TUTOR (propio) y COORDINADOR (cualquiera) modificar el estado y comentarios de una guardia.

#### Scenario: TUTOR marca guardia como realizada
- **WHEN** un TUTOR cambia el estado de su guardia a "Realizada" y agrega un comentario
- **THEN** la guardia se actualiza con estado "Realizada" y el nuevo comentario

#### Scenario: TUTOR no puede editar guardia de otro
- **WHEN** un TUTOR intenta editar una guardia que no le pertenece
- **THEN** el sistema retorna 403 Forbidden

### Requirement: Exportar guardias

El sistema SHALL permitir a COORDINADOR/ADMIN (con permiso `guardias:ver-admin`) exportar el registro de guardias a un archivo descargable (xlsx o csv), aplicando los mismos filtros del listado.

#### Scenario: Exportación exitosa de guardias
- **WHEN** un COORDINADOR exporta guardias con filtros de materia y fechas
- **THEN** el sistema descarga un archivo con las guardias filtradas y sus datos completos

#### Scenario: TUTOR sin permiso de exportación
- **WHEN** un TUTOR sin permiso `guardias:ver-admin` intenta exportar guardias
- **THEN** el sistema retorna 403 Forbidden

### Requirement: Scope multi-tenant en guardias

Toda operación sobre guardias SHALL filtrar por tenant_id del usuario autenticado.

#### Scenario: Aislamiento de guardias entre tenants
- **WHEN** un usuario del Tenant A lista guardias
- **THEN** NO se incluyen guardias del Tenant B
