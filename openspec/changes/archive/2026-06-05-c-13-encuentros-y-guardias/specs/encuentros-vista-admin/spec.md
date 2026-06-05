## ADDED Requirements

### Requirement: Vista admin de encuentros (F6.5)

El sistema SHALL proporcionar a COORDINADOR y ADMIN (con permiso `encuentros:ver-admin`) una vista transversal de todos los encuentros del tenant sin restricción por docente creador. La vista es de consulta (no permite crear/modificar en nombre de otro).

#### Scenario: COORDINADOR ve todos los encuentros del tenant
- **WHEN** un COORDINADOR con permiso `encuentros:ver-admin` lista encuentros
- **THEN** el sistema retorna encuentros de todos los docentes del tenant
- **AND** incluye el nombre del docente creador en cada instancia/slot

#### Scenario: Vista admin filtrada por docente
- **WHEN** un ADMIN lista encuentros filtrados por un usuario_id específico
- **THEN** el sistema retorna solo los encuentros creados por ese usuario

#### Scenario: PROFESOR sin permiso admin no ve encuentros de otros
- **WHEN** un PROFESOR sin permiso `encuentros:ver-admin` lista encuentros sin filtro
- **THEN** el sistema retorna solo sus propios encuentros (scope propio)
