## ADDED Requirements

### Requirement: Crear slot de encuentro recurrente (F6.1, RN-13)

El sistema SHALL permitir a usuarios con permiso `encuentros:gestionar` crear un slot recurrente definiendo: materia, título, hora, día de la semana, fecha de inicio, cantidad de semanas y enlace de videoconferencia. El sistema SHALL generar automáticamente N instancias (una por semana) a partir de ese slot.

#### Scenario: Creación exitosa de slot recurrente genera N instancias
- **WHEN** un PROFESOR crea un slot recurrente con `cant_semanas = 4` y `fecha_inicio = 2026-03-02` (lunes)
- **THEN** el sistema crea el slot y 4 instancias: 2026-03-02, 2026-03-09, 2026-03-16, 2026-03-23
- **AND** todas las instancias tienen estado "Programado"
- **AND** retorna 201 Created con el slot y sus instancias

#### Scenario: Slot recurrente con cant_semanas = 0 es rechazado
- **WHEN** un PROFESOR crea un slot recurrente con `cant_semanas = 0`
- **THEN** el sistema retorna 422 Unprocessable Entity indicando que `cant_semanas` debe ser > 0 para modo recurrente

### Requirement: Crear encuentro único (F6.2, RN-13)

El sistema SHALL permitir a usuarios con permiso `encuentros:gestionar` crear un encuentro de fecha única sin recurrencia, definiendo materia, título, fecha, hora y enlace de videoconferencia. La instancia se crea sin slot asociado (slot_id = null).

#### Scenario: Creación exitosa de encuentro único
- **WHEN** un PROFESOR crea un encuentro único con fecha específica y sin slot asociado
- **THEN** el sistema crea una sola instancia con slot_id = null, estado "Programado"
- **AND** retorna 201 Created

### Requirement: Listar slots del usuario

El sistema SHALL permitir a usuarios con permiso `encuentros:gestionar` listar sus propios slots. COORDINADOR y ADMIN con permiso `encuentros:ver-admin` SHALL poder listar slots de cualquier docente del tenant.

#### Scenario: PROFESOR lista sus propios slots
- **WHEN** un PROFESOR lista sus slots
- **THEN** el sistema retorna solo los slots donde el PROFESOR tiene asignación activa en la materia

#### Scenario: COORDINADOR lista slots de todo el tenant
- **WHEN** un COORDINADOR lista slots sin filtro de materia
- **THEN** el sistema retorna todos los slots del tenant

### Requirement: Editar slot de encuentro

El sistema SHALL permitir a usuarios con permiso `encuentros:gestionar` editar campos del slot (título, hora, meet_url). La modificación NO afecta las instancias ya generadas.

#### Scenario: Edición exitosa de slot
- **WHEN** un PROFESOR modifica la hora de un slot existente
- **THEN** el sistema actualiza el slot
- **AND** las instancias ya generadas mantienen sus datos originales

### Requirement: Eliminar slot (soft-delete)

El sistema SHALL permitir a usuarios con permiso `encuentros:gestionar` eliminar un slot. La operación es soft-delete: el slot y todas sus instancias se marcan como eliminadas (no se borran físicamente).

#### Scenario: Soft-delete de slot elimina lógicamente slot e instancias
- **WHEN** un PROFESOR elimina un slot
- **THEN** el slot se marca como eliminado (deleted_at no nulo)
- **AND** todas las instancias asociadas se marcan como eliminadas
- **AND** no aparece en listados normales pero permanece en BD

### Requirement: Scope multi-tenant en slots

Toda operación sobre slots SHALL filtrar por tenant_id del usuario autenticado. Un usuario de un tenant NO puede ver ni modificar slots de otro tenant.

#### Scenario: Aislamiento de slots entre tenants
- **WHEN** un usuario del Tenant A lista slots
- **THEN** NO se incluyen slots del Tenant B en los resultados
