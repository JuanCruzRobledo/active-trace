## ADDED Requirements

### Requirement: Estado independiente de cada instancia (RN-14)

Cada instancia de encuentro SHALL tener su propio estado (Programado / Realizado / Cancelado) independiente del slot que la originó. Modificar el estado de una instancia NO afecta a otras instancias ni al slot.

#### Scenario: Cancelar una instancia no afecta las demás
- **WHEN** un PROFESOR cancela una instancia de un slot con 10 instancias
- **THEN** solo esa instancia cambia a estado "Cancelado"
- **AND** las otras 9 instancias permanecen en su estado original

#### Scenario: Instancia se crea con estado Programado por defecto
- **WHEN** se crea una instancia (desde slot o individual)
- **THEN** su estado inicial es "Programado"

### Requirement: Editar instancia de encuentro (F6.3)

El sistema SHALL permitir a usuarios con permiso `encuentros:gestionar` modificar los campos editables de una instancia: estado, meet_url, video_url (disponible post-encuentro), comentario.

#### Scenario: Edición de meet_url y comentario
- **WHEN** un PROFESOR actualiza el meet_url y el comentario de una instancia
- **THEN** el sistema guarda los nuevos valores y retorna la instancia actualizada

#### Scenario: Registro de grabación post-encuentro
- **WHEN** un PROFESOR marca la instancia como "Realizado" y agrega video_url
- **THEN** la instancia queda con estado "Realizado" y el enlace de grabación registrado

#### Scenario: Usuario sin permiso no puede editar
- **WHEN** un usuario sin permiso `encuentros:gestionar` intenta editar una instancia
- **THEN** el sistema retorna 403 Forbidden

### Requirement: Listar instancias con filtros

El sistema SHALL permitir listar instancias con filtros por materia, rango de fechas (desde/hasta), estado y slot_id. PROFESOR ve solo sus instancias (scope propio). COORDINADOR/ADMIN ve todas.

#### Scenario: Listado filtrado por materia y rango de fechas
- **WHEN** un COORDINADOR lista instancias con `materia_id=X`, `desde=2026-03-01`, `hasta=2026-03-31`
- **THEN** el sistema retorna solo las instancias de esa materia en ese rango de fechas

#### Scenario: PROFESOR ve solo instancias de sus materias
- **WHEN** un PROFESOR lista instancias sin filtro
- **THEN** el sistema retorna solo instancias de materias donde tiene asignación activa

### Requirement: Crear instancia independiente (sin slot)

El sistema SHALL permitir crear una instancia de encuentro suelta (slot_id = null) para encuentros no planificados como recurrentes.

#### Scenario: Creación de instancia independiente
- **WHEN** un PROFESOR crea una instancia sin especificar slot_id
- **THEN** la instancia se crea con slot_id = null y estado "Programado"

### Requirement: Scope multi-tenant en instancias

Toda operación sobre instancias SHALL filtrar por tenant_id del usuario autenticado.

#### Scenario: Aislamiento de instancias entre tenants
- **WHEN** un usuario del Tenant A lista instancias
- **THEN** NO se incluyen instancias del Tenant B
